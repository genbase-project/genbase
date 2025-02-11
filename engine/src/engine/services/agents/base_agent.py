from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import importlib.util
import inspect
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.config.workflow_config import WorkflowConfigService

from engine.db.session import SessionLocal
from engine.services.agents.chat_history import AgentError, ChatHistoryManager
from engine.services.execution.model import ModelService
from engine.services.execution.state import StateService, AgentState
from engine.services.core.module import ModuleService, RelationType
from engine.services.execution.workflow import (
    ActionInfo,
    WorkflowService,
    WorkflowMetadataResult,
    WorkflowActionMetadata
)
from engine.services.storage.repository import RepoService
from engine.utils.logging import logger
from pathlib import Path


@dataclass
class AgentServices:
    """Container for all services required by agents"""
    model_service: ModelService
    workflow_service: WorkflowService
    stage_state_service: StateService
    repo_service: RepoService
    module_service: ModuleService

@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    workflow: str
    user_input: str
    session_id: Optional[str] = None


@dataclass
class Action:
    """Represents an action with both schema and implementation"""
    name: str
    description: str
    schema: Dict[str, Any]  # OpenAPI function schema
    function: Callable[..., Any]  # Actual function implementation

class BaseAgent(ABC):
    """Base class for all agents with shared infrastructure"""

    def __init__(self, services: AgentServices):
        self.services = services
        self.history_manager = ChatHistoryManager()
        self.workflow_config_service = WorkflowConfigService()

    def create_xml_prompt(self, question: str, options: List[dict]) -> str:
        """Create an XML prompt with the specified question and options.
        
        Args:
            question: The question to ask the user
            options: List of dicts with 'text' and optional 'description' keys
        
        Example:
            options = [
                {"text": "Yes", "description": "Continue with changes"},
                {"text": "No", "description": "Cancel the operation"}
            ]
        """
        option_tags = []
        for opt in options:
            desc = f' description="{opt["description"]}"' if "description" in opt else ''
            option_tags.append(f'<option{desc}>{opt["text"]}</option>')
            
        return f"""<user_prompt>
<question>
{question}
</question>
<options>
{"".join(option_tags)}
</options>
</user_prompt>"""

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type"""
        pass

    @property
    @abstractmethod
    def default_actions(self) -> List[Action]:
        """Return list of default actions available to this agent type"""
        pass


    async def process_request(self, context: AgentContext) -> Dict[str, Any]:
        """Standard request processing flow"""
        try:            



            # Set executing state
            self.services.stage_state_service.set_executing(context.module_id)
            
            try:
                # Get chat history
                messages = self.history_manager.get_chat_history(
                    context.module_id,
                    context.workflow,
                    context.session_id
                )
                
                # Add user input to history
                self.history_manager.add_to_history(
                    context.module_id,
                    context.workflow,
                    "user",
                    context.user_input,
                    session_id=context.session_id
                )

                messages.append({
                    "role": "user",
                    "content": context.user_input
                })
                
                # Process the workflow according to agent type
                result = await self._process_workflow(context, messages, [])
                
                return result
                
            finally:
                # Reset state when done
                self.services.stage_state_service.set_standby(context.module_id)
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            # Ensure state is reset on error
            self.services.stage_state_service.set_standby(context.module_id)
            raise AgentError(f"Failed to process request: {str(e)}")

    async def get_shared_actions(self, module_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, ActionInfo]]:
        """
        Get shared actions from all connected modules
        
        Args:
            module_id: Module ID to get shared actions for
            
        Returns:
            Tuple of:
            - List of shared actions in tool format
            - Dict mapping tool names to ActionInfo
        """
        tools = []
        action_map = {}
        try:
            # Get all modules with CONNECTION relation
            connected_modules = self.services.module_service.get_linked_modules(
                module_id=module_id,
                relation_type=RelationType.CONNECTION
            )
            
            for module in connected_modules:
                # Get shared actions metadata
                metadata = self.services.workflow_service.get_shared_actions_metadata(module.module_id)
                
                for action in metadata.actions:
                    if not action.error:
                        tool_name = f"{module.module_id}:{action.name}"
                        tools.append({
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": action.description or "",
                                "parameters": {} if action.metadata.parameters is None else action.metadata.parameters,
                            }
                        })
                        
                        action_map[tool_name] = ActionInfo(
                            module_id=module.module_id,
                            workflow="",  # Not part of a workflow
                            action_path=action.action,
                            name=action.name,
                            description=action.description
                        )
                    
            return tools, action_map
        except Exception as e:
            logger.error(f"Failed to get shared actions: {str(e)}")
            return [], {}
            
    async def get_workflow_metadata(self, context: AgentContext) -> WorkflowMetadataResult:
        """Get workflow metadata"""
        try:
            workflow = self.services.workflow_service.get_workflow_metadata(
                module_id=context.module_id,
                workflow=context.workflow
            )
            return workflow
        except Exception as e:
            logger.error(f"Error getting workflow metadata: {str(e)}")
            raise AgentError(f"Failed to get workflow metadata: {str(e)}")

    async def get_workflow_actions(
        self,
        context: AgentContext,
        workflow_actions: List[WorkflowActionMetadata]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, ActionInfo]]:
        """Convert workflow actions to tools format with action mapping"""
        tools = []
        action_map = {}
        
        for action in workflow_actions:
            if not action.metadata:
                continue

            action_info = ActionInfo(
                module_id=context.module_id,
                workflow=context.workflow,
                action_path=action.action,
                name=action.name,
                description=action.description or action.metadata.description
            )
            
            tool = {
                "type": "function",
                "function": {
                    "name": action_info.name,
                    "description": action_info.description,
                    "parameters": {} if action.metadata.parameters is None else action.metadata.parameters,
                }
            }
            
            tools.append(tool)
            action_map[action_info.name] = action_info
            
        return tools, action_map

    def _add_instruction_prompts(
        self,
        messages: List[Dict[str, str]],
        workflow_data: WorkflowMetadataResult,
        context: AgentContext
    ) -> List[Dict[str, str]]:
        """Add instruction prompts to messages"""
        instructions = [self._get_base_instructions()]

        instructions.append(f"Current workflow is {context.workflow}")
        
        if workflow_data.instructions:
            instructions.append(workflow_data.instructions)
            
        combined_instructions = "\n\n".join(instructions)
        
        if not any(msg["role"] == "system" for msg in messages):
            messages.insert(0, {
                "role": "system",
                "content": combined_instructions
            })
        else:
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = f"{msg['content']}\n\n{combined_instructions}"
                    break
                    
        return messages

    @abstractmethod
    def _get_base_instructions(self) -> str:
        """Get base instructions for the agent type"""
        pass

    @abstractmethod
    async def _process_workflow(
        self,
        context: AgentContext,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process workflow according to specific agent type"""
        pass

    async def execute_function_by_name(
        self,
        module_id: str,
        file_path: str,
        function_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dynamically execute a function from a given file by name
        
        Args:
            module_id: ID of the module containing the function
            file_path: Path to the Python file containing the function (relative to module root)
            function_name: Name of the function to execute
            params: Optional parameters to pass to the function
            
        Returns:
            Dictionary containing the result of the function execution
        """
        try:
            # Get absolute path to module
            module_path = self.services.module_service.get_module_path(module_id)
            full_path = module_path / file_path
            
            if not full_path.exists():
                raise AgentError(f"Function file not found: {file_path}")
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                f"dynamic_module_{function_name}",
                str(full_path)
            )
            if not spec or not spec.loader:
                raise AgentError(f"Could not load module spec for {file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get function from module
            if not hasattr(module, function_name):
                raise AgentError(f"Function {function_name} not found in {file_path}")
                
            function = getattr(module, function_name)
            if not callable(function):
                raise AgentError(f"{function_name} in {file_path} is not callable")

            # Inspect function signature
            sig = inspect.signature(function)
            if params is None:
                params = {}
                
            # Filter only parameters that exist in function signature
            valid_params = {}
            for param_name, param in sig.parameters.items():
                if param_name in params:
                    valid_params[param_name] = params[param_name]
                elif param.default is inspect.Parameter.empty:
                    raise AgentError(f"Required parameter {param_name} missing for function {function_name}")

            # Execute function
            result = function(**valid_params)
            
            # Handle coroutines
            if inspect.iscoroutine(result):
                import asyncio
                result = await result

            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_workflow_default_actions(self, workflow: str, module_id: str) -> List[Action]:
        """Get default actions for specific workflow type"""
        module_path = self.services.module_service.get_module_path(module_id)
        
        # Get kit config
        with open(module_path / "kit.yaml") as f:
            import yaml
            kit_config = yaml.safe_load(f)
            
        workflow_config = self.workflow_config_service.get_workflow_config(workflow, kit_config)
        actions = []
        for wf_action in workflow_config.default_actions:
            actions.append(Action(
                name=wf_action.name,
                description=wf_action.description,
                schema=wf_action.schema,
                function=wf_action.function
            ))
        return actions
