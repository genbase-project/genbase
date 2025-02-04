from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.config.workflow_config import WorkflowConfigService
from engine.db.models import ChatHistory, WorkflowStatus
from engine.db.session import SessionLocal
from engine.services.execution.model import ModelService
from engine.services.execution.stage_state import StageStateService, AgentStage, AgentState
from engine.services.core.module import ModuleService, RelationType
from engine.services.execution.workflow import ActionInfo, WorkflowService
from engine.services.storage.repository import RepoService
from engine.utils.logging import logger

class AgentError(Exception):
    """Base exception for agent operations"""
    pass

@dataclass
class AgentServices:
    """Container for all services required by agents"""
    model_service: ModelService
    workflow_service: WorkflowService
    stage_state_service: StageStateService
    repo_service: RepoService
    module_service: ModuleService

@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    workflow: str
    user_input: str

class ChatHistoryManager:
    """Manages chat history operations"""
    
    def __init__(self):
        self._db = SessionLocal()
    
    def get_chat_history(self, module_id: str, workflow: str) -> List[Dict[str, Any]]:
        """Get chat history for a module and workflow"""
        try:
            with self._db as db:
                stmt = (
                    select(ChatHistory)
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.section == workflow
                    )
                    .order_by(ChatHistory.timestamp.asc())
                )
                messages = db.execute(stmt).scalars().all()

                history = []
                for msg in messages:
                    message = {
                        "role": msg.role,
                        "content": msg.content
                    }
                    if msg.message_type in ["tool_call", "tool_result"]:
                        if msg.message_type == "tool_call":
                            message["tool_calls"] = msg.tool_data
                        else:
                            message["tool_results"] = msg.tool_data
                    history.append(message)
                return history
        except Exception as e:
            raise AgentError(f"Failed to get chat history: {str(e)}")

    def add_to_history(
        self,
        module_id: str,
        workflow: str,
        role: str,
        content: str,
        message_type: str = "text",
        tool_data: Optional[Dict[str, Any]] = None
    ):
        """Add message to chat history"""
        try:
            with self._db as db:
                chat_message = ChatHistory(
                    module_id=module_id,
                    section=workflow,
                    role=role,
                    content=content or "Empty message",
                    timestamp=datetime.now(UTC),
                    message_type=message_type,
                    tool_data=tool_data
                )
                db.add(chat_message)
                db.commit()
        except Exception as e:
            raise AgentError(f"Failed to add to history: {str(e)}")


@dataclass
class Action:
    """Represents an action with both schema and implementation"""
    name: str
    description: str
    schema: Dict[str, Any]  # OpenAPI function schema
    function: Callable[..., Any]  # Actual function implementation

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json

from engine.utils.logging import logger
from engine.services.execution.workflow import ActionInfo, WorkflowService
from engine.services.core.module import ModuleService, RelationType
from engine.services.execution.model import ModelService
from engine.services.execution.stage_state import StageStateService
from engine.services.storage.repository import RepoService

@dataclass
class AgentServices:
    """Container for all services required by agents"""
    model_service: ModelService
    workflow_service: WorkflowService
    stage_state_service: StageStateService
    repo_service: RepoService
    module_service: ModuleService

@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    workflow: str
    user_input: str

@dataclass
class Action:
    """Represents an action with both schema and implementation"""
    name: str
    description: str
    schema: Dict[str, Any]  # OpenAPI function schema
    function: Any  # Actual function implementation

class AgentError(Exception):
    """Base exception for agent operations"""
    pass

class BaseAgent(ABC):
    """Base class for all agents with shared infrastructure"""

    def __init__(self, services: AgentServices):
        self.services = services
        self.history_manager = ChatHistoryManager()
        self.workflow_config_service = WorkflowConfigService()

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type (tasker or coder)"""
        pass

    @property
    @abstractmethod
    def default_actions(self) -> List[Action]:
        """Return list of default actions available to this agent type"""
        pass



    def get_completed_workflows(self, module_id: str) -> Set[str]:
        """Get set of completed workflows for a module"""
        try:
            with SessionLocal() as db:
                stmt = (
                    select(WorkflowStatus)
                    .where(
                        WorkflowStatus.module_id == module_id,
                        WorkflowStatus.is_completed == True
                    )
                )
                results = db.execute(stmt).scalars().all()
                return {ws.workflow_type for ws in results}
        except Exception as e:
            logger.error(f"Error getting completed workflows: {str(e)}")
            return set()

    def verify_prerequisites(self, module_id: str, workflow: str) -> bool:
        """Verify if all prerequisite workflows are completed"""
        try:
            # Get workflow config
            config = self.workflow_config_service.get_workflow_config(workflow)
            
            # Get completed workflows
            completed = self.get_completed_workflows(module_id)
            
            # Check if all prerequisites are completed
            return self.workflow_config_service.can_execute_workflow(workflow, completed)
            
        except Exception as e:
            logger.error(f"Error verifying prerequisites: {str(e)}")
            return False


    async def process_request(self, context: AgentContext) -> Dict[str, Any]:
        """Standard request processing flow"""
        try:            

            if not self.verify_prerequisites(context.module_id, context.workflow):
                raise AgentError(
                    f"Cannot execute workflow '{context.workflow}' - prerequisites not met. "
                    "Please complete required workflows first."
                )

            # Set executing state
            self.services.stage_state_service.set_executing(context.module_id)
            
            try:
                # Get chat history
                messages = self.history_manager.get_chat_history(
                    context.module_id,
                    context.workflow
                )
                
                # Add user input to history
                self.history_manager.add_to_history(
                    context.module_id,
                    context.workflow,
                    "user",
                    context.user_input
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


    async def get_combined_workflow_metadata(self, context: AgentContext) -> Dict[str, Any]:
        """Get combined workflow metadata from main and shared workflows"""
        try:
            # Get main workflow metadata - Remove await as this is not async
            main_workflow = self.services.workflow_service.get_workflow_metadata(
                module_id=context.module_id,
                workflow=context.workflow
            )
            
            # Get connected modules
            connected_modules = self.services.module_service.get_linked_modules(
                module_id=context.module_id,
                relation_type=RelationType.CONNECTION
            )
            
            combined_instructions = [main_workflow.get("instructions", "")]
            combined_actions = main_workflow.get("actions", [])
            combined_requirements = set(main_workflow.get("requirements", []))
            
            # Process connected modules
            for connected_module in connected_modules:
                try:
                    # Remove await here as well
                    share_workflow = self.services.workflow_service.get_workflow_metadata(
                        module_id=connected_module.module_id,
                        workflow="share"
                    )
                    
                    if share_workflow.get("instructions"):
                        module_context = f"\nShared instructions from {connected_module.module_name}:\n"
                        combined_instructions.extend([module_context, share_workflow["instructions"]])
                    
                    # Add shared actions with source information
                    for action in share_workflow.get("actions", []):
                        shared_action = {
                            **action,
                            "source_module_id": connected_module.module_id,
                            "source_module_name": connected_module.module_name,
                            "source_workflow": "share"
                        }
                        combined_actions.append(shared_action)
                    
                    combined_requirements.update(share_workflow.get("requirements", []))
                    
                except Exception as e:
                    logger.warning(f"Failed to process share workflow from {connected_module.module_id}: {str(e)}")
                    continue
            
            return {
                "instructions": "\n".join(filter(None, combined_instructions)),
                "actions": combined_actions,
                "requirements": list(combined_requirements)
            }
            
        except Exception as e:
            logger.error(f"Error getting combined workflow metadata: {str(e)}")
            raise AgentError(f"Failed to get workflow metadata: {str(e)}")

    # Also update get_workflow_actions to remove await if the methods it calls aren't async
    async def get_workflow_actions(
        self,
        context: AgentContext,
        workflow_actions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, ActionInfo]]:
        """Convert workflow actions to tools format with action mapping"""
        tools = []
        action_map = {}
        
        for action in workflow_actions:
            metadata = action.get("metadata")
            if not metadata:
                continue
                
            source_module_id = action.get("source_module_id", context.module_id)
            source_workflow = action.get("source_workflow", context.workflow)
            
            action_info = ActionInfo(
                module_id=source_module_id,
                workflow=source_workflow,
                action_path=action["action"],
                name=action["name"],
                description=action.get("description", "") or metadata.description,
                source_module_name=action.get("source_module_name")
            )
            
            tool = {
                "type": "function",
                "function": {
                    "name": action_info.name,
                    "description": action_info.description,
                    "parameters": metadata.parameters
                }
            }
            
            tools.append(tool)
            action_map[action_info.name] = action_info
            
        return tools, action_map

    def _add_instruction_prompts(
        self,
        messages: List[Dict[str, str]],
        workflow_data: Dict[str, Any],
        context: AgentContext
    ) -> List[Dict[str, str]]:
        """Add instruction prompts to messages"""
        instructions = [self._get_base_instructions()]

        instructions.append(f"Current workflow is {context.workflow}")
        
        if workflow_data.get("instructions"):
            instructions.append(workflow_data["instructions"])
            
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

    def get_workflow_default_actions(self, workflow: str) -> List[Action]:
        """Get default actions for specific workflow type"""
        workflow_config = self.workflow_config_service.get_workflow_config(workflow)
        actions = []
        for wf_action in workflow_config.default_actions:
            actions.append(Action(
                name=wf_action.name,
                description=wf_action.description,
                schema=wf_action.schema,
                function=wf_action.function
            ))
        return actions