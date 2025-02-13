from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
from engine.services.core.kit import KitConfig
from engine.services.execution.action import FunctionMetadata
from engine.services.execution.model import ModelService
from engine.services.execution.state import StateService
from engine.services.execution.workflow import (
    EnhancedWorkflowAction,
    WorkflowExecutionResult,
    WorkflowService,
    WorkflowMetadataResult,
    ActionInfo
)
from engine.services.agents.chat_history import ChatHistoryManager
from engine.services.core.module import ModuleService, RelationType
from engine.utils.logging import logger

@dataclass
class AgentServices:
    """Essential services required by all agents"""
    model_service: ModelService     # For LLM interactions
    workflow_service: WorkflowService  # For workflow execution
    module_service: ModuleService   # For module management
    state_service: StateService     # For agent state management

@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    workflow: str
    user_input: str
    session_id: Optional[str] = None

class BaseAgent(ABC):
    """Next generation base agent with core functionality"""
    
    def __init__(self, services: AgentServices):
        """Initialize base agent with required services"""
        self.services = services
        self.history_manager = ChatHistoryManager()
        self.context: Optional[AgentContext] = None
        self.tag_elements = self._get_tag_elements()
        self.tools: List[Dict[str, Any]] = []
        self.system_prompt: Optional[str] = None

    def _get_tag_elements(self) -> Dict[str, str]:
        """Get XML element templates and descriptions"""
        return {
            "user_prompt":{"format": """
<user_prompt>
<question>
Your question here
</question>
<options>
<option description="Description of what this option means">Option text</option>
</options>
</user_prompt>""",
"use": "Prompt the user with a question and multiple choice options"}

,
            
            "code_change": {"format":"""
<code_change file="path/to/file">
<original>
Original code to replace
</original>
<updated>
Updated code
</updated>
<description>
Explanation of the change
</description>
</code_change>""", "use":"Describe a code change with original and updated code"},
        }

    async def build_context(
        self,
        agent_instructions: str = None,
        action_names: Optional[List[str]] = None,
        include_shared_actions: bool = False,
        required_xml_elements: List[str] = None,
        custom_instructions: Optional[str] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Build system prompt with selected actions as tools
        
        Args:
            workflow_instructions: Optional workflow-specific instructions
            action_names: List of action names to include, or None for all actions
            include_shared_actions: Whether to include shared actions as tools
            required_xml_elements: List of XML element templates to include
            custom_instructions: Additional instructions to append
            
        Returns:
            Tuple of (system prompt, list of tools)
        """
        if not self.context:
            raise ValueError("No active context")
            
        parts: Dict[str, str] = {"Agent Instructions": agent_instructions}
        tools = []

        # Get workflow metadata
        workflow_data: WorkflowMetadataResult = self.services.workflow_service.get_workflow_metadata(
            self.context.module_id,
            self.context.workflow
        )

        if action_names is None:  # Include all actions
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": action.name,
                        "description": action.description,
                        "parameters": action.metadata.parameters if action.metadata else {}
                    }
                }
                for action in workflow_data.actions
            ]
        else:  # Include only specified actions
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": action.name,
                        "description": action.description,
                        "parameters": action.metadata.parameters if action.metadata else {}
                    }
                }
                for action in workflow_data.actions
                if action.name in action_names
            ]

        # Add tool descriptions to prompt
        workflow_tool_descriptions = []
        for tool in tools:
            workflow_tool_descriptions.append(
                f"- {tool['function']['name']}: {tool['function']['description']}"
            )

        if workflow_tool_descriptions:
            parts["Available tools"]= "\n".join(workflow_tool_descriptions)

        # Add XML element documentation
        if required_xml_elements:
            xml_docs = []
            for element in required_xml_elements:
                if element in self.tag_elements:
                    xml_docs.append(f"Element f{element}\n format: {self.tag_elements[element]['format']}\n use: {self.tag_elements[element]['use']}")
            if xml_docs:
                parts["Tag Elements"]= "\n\n".join(xml_docs)

        # Add custom instructions at the end if provided
        if custom_instructions:
            parts["Additional Instructions"]=custom_instructions

        final_instruction = ""
        for key, value in parts.items():
            if value:
                final_instruction += f"\n\n##{key}:\n{value}"
            
        self.tools = tools
        self.system_prompt = final_instruction
        return final_instruction, tools

    def add_to_history(
        self, 
        role: str,
        content: str,
        message_type: str = "text", 
        tools_info: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        """
        Add a message to chat history
        
        Args:
            role: The role of the message sender (user/assistant/tool)
            content: The message content
            message_type: Message type (text/tool_call/tool_result)
            tools_info: Optional list of tool info dictionaries
            tool_call_id: Optional ID of the tool call this message is responding to
            tool_name: Optional name of the tool this message is from
        """
        if not self.context:
            raise ValueError("No active context")

        message = {
            "role": role,
            "content": content
        }

        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        if tool_name:
            message["name"] = tool_name
        
        self.history_manager.add_to_history(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            role=role,
            content=content,
            message_type=message_type,
            tool_data=tools_info,
            session_id=self.context.session_id
        )

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get complete chat history"""
        if not self.context:
            raise ValueError("No active context")
            
        return self.history_manager.get_chat_history(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            session_id=self.context.session_id
        )

    async def execute_workflow_action(
        self,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a workflow action"""
        try:
            if not self.context:
                raise ValueError("No active context")

            action_info = ActionInfo(
                module_id=self.context.module_id,
                workflow=self.context.workflow,
                action_path="",  # Will be filled by workflow service
                name=action_name
            )

            result: WorkflowExecutionResult = self.services.workflow_service.execute_workflow_action(
                module_id=self.context.module_id,
                workflow=self.context.workflow,
                action_info=action_info,
                parameters=parameters
            )

            return result
        except Exception as e:
            logger.error(f"Error executing workflow action: {str(e)}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        tool_choice: Optional[str] = "auto",
        **kwargs
    ):
        """Wrapper for model service chat completion that handles tools and history"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Get current chat history
            history = self.get_chat_history()

            # Always include system message first if we have one
            all_messages = []
            if self.system_prompt:
                all_messages.append({"role": "system", "content": self.system_prompt})
            
            # Add history and new messages
            all_messages.extend(history + messages)
            
            # Execute chat completion with current tools
            response = await self.services.model_service.chat_completion(
                messages=all_messages,
                stream=stream,
                tools=self.tools if self.tools else None,
                tool_choice=tool_choice if self.tools else None,
                **kwargs
            )
            
            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise

    async def process_request(self, context: AgentContext) -> Dict[str, Any]:
        """Process an agent request"""
        try:
            self.context = context
            # Get workflow metadata
            workflow_data: WorkflowMetadataResult =  self.services.workflow_service.get_workflow_metadata(
                context.module_id,
                context.workflow
            )
            
            # Add user input to history
            self.add_to_history("user", context.user_input)

            # Process workflow
            result = await self.process_workflow(context, workflow_data)

            return result
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise
        finally:
            self.context = None  # Clear context

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type identifier"""
        pass

    @abstractmethod
    async def process_workflow(
        self,
        context: AgentContext,
        workflow_data: WorkflowMetadataResult
    ) -> Dict[str, Any]:
        """Process a workflow request"""
        pass
