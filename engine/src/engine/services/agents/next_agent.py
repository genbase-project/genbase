from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from engine.services.core.kit import KitConfig
from engine.services.execution.model import ModelService
from engine.services.execution.workflow import (
    EnhancedWorkflowAction,
    WorkflowService,
    WorkflowMetadataResult,
    ActionInfo,
    WorkflowActionMetadata
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

@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    workflow: str
    user_input: str
    session_id: Optional[str] = None

class NextBaseAgent(ABC):
    """Next generation base agent with core functionality"""
    
    def __init__(self, services: AgentServices):
        """Initialize base agent with required services"""
        self.services = services
        self.history_manager = ChatHistoryManager()
        self.context: Optional[AgentContext] = None
        self.tag_elements = self._get_tag_elements()
        self.tools: List[EnhancedWorkflowAction] = []

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
        workflow_data: WorkflowMetadataResult = await self.services.workflow_service.get_workflow_metadata(
            self.context.module_id,
            self.context.workflow
        )

        if action_names is None:  # Include all actions
            tools = [action for action in workflow_data.actions]
        else:  # Include only specified actions
            tools = [
                action for action in workflow_data.actions
                if action.name in action_names
            ]

        # Add selected workflow actions to tools
        workflow_tool_descriptions = []
        for action in tools:
            workflow_tool_descriptions.append(
                f"- {action.name}: {action.description or 'No description'}"
            )

        if workflow_tool_descriptions:
            parts["Available tools"]= "\n".join(workflow_tool_descriptions)


        # Add requested XML element documentation
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
            
        return final_instruction, tools

    def add_to_history(
        self,
        role: str,
        content: str,
        tool_info: List[Dict[str, Any]] = None
    ):
        """Add a message to chat history"""
        if not self.context:
            raise ValueError("No active context")
            
        message_type = "text"
        tool_data = None

        for info in tool_info:
            message_type = info["type"]
            tool_data = info["data"]

        self.history_manager.add_to_history(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            role=role,
            content=content,
            message_type=message_type,
            tool_data=tool_data,
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

            workflow_data = await self.services.workflow_service.get_workflow_metadata(
                self.context.module_id,
                self.context.workflow
            )
            
            # Find matching action
            action = next(
                (a for a in workflow_data.actions if a.name == action_name),
                None
            )
            if not action:
                raise ValueError(f"Action {action_name} not found in workflow")

            result = await self.services.workflow_service.execute_workflow_step(
                module_id=self.context.module_id,
                workflow=self.context.workflow,
                action_info=ActionInfo(
                    module_id=self.context.module_id,
                    workflow=self.context.workflow,
                    action_path=action.action,
                    name=action.name,
                    description=action.description
                ),
                parameters=parameters
            )

            return result
        except Exception as e:
            logger.error(f"Error executing workflow action: {str(e)}")
            raise

    async def execute_shared_action(
        self,
        module_id: str,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a shared action from another module"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Verify connection access
            if not await self.services.module_service.verify_connection_access(
                self.context.module_id,
                module_id
            ):
                raise ValueError(f"No connection access to module {module_id}")

            # Get shared actions
            metadata = await self.services.workflow_service.get_shared_actions_metadata(
                module_id
            )

            # Find matching action
            action = next(
                (a for a in metadata.actions if a.name == action_name),
                None
            )
            if not action:
                raise ValueError(f"Shared action {action_name} not found in module {module_id}")

            result = await self.services.workflow_service.execute_shared_action(
                module_id=self.context.module_id,
                workflow=self.context.workflow,
                action_info=ActionInfo(
                    module_id=module_id,
                    workflow="",
                    action_path=action.action,
                    name=action.name,
                    description=action.description
                ),
                parameters=parameters
            )

            return result
        except Exception as e:
            logger.error(f"Error executing shared action: {str(e)}")
            raise

    async def chat_completion(
        self,
        user_input: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a chat completion with current history and tools"""
        messages = self.get_chat_history()
        messages.append({"role": "user", "content": user_input})

        response = await self.services.model_service.chat_completion(
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None
        )

        return response.choices[0].message

    async def process_request(self, context: AgentContext) -> Dict[str, Any]:
        """Process an agent request"""
        try:
            self.context = context

            # Get workflow metadata
            workflow_data = await self.services.workflow_service.get_workflow_metadata(
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
