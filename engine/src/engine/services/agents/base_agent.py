from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import uuid
import xml.etree.ElementTree as ET
import xmltodict
from litellm import ChatCompletionMessageToolCall, Choices
from engine.services.core.kit import KitConfig
from engine.services.execution.action import FunctionMetadata
from engine.services.execution.custom_actions import CustomActionManager
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
from engine.services.execution.workflow_store import WorkflowStoreInfo, WorkflowStoreRecord, WorkflowStoreService
from engine.services.storage.repository import RepoService
from engine.services.agents.agent_utils import AgentUtils
from loguru import logger
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class GimlResponse:
    """Structured response for GIML elements"""
    id: str                  # ID of the GIML element
    giml_type: str          # Type of GIML element (select, code_diff, etc)
    response_value: Optional[str]  # User's response value if provided
    structured_giml: Dict    # Full GIML structure as dictionary


@dataclass
class AgentServices:
    """Essential services required by all agents"""
    model_service: ModelService     # For LLM interactions
    workflow_service: WorkflowService  # For workflow execution
    module_service: ModuleService   # For module management
    state_service: StateService     # For agent state management
    repo_service: RepoService       # For repository operations

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
        self.tag_elements = self.get_giml()
        self.tools: List[Dict[str, Any]] = []
        self.system_prompt: Optional[str] = None
        self._utils: Optional[AgentUtils] = None


        # Initialize the custom action manager
        self.action_manager = CustomActionManager()



    def register_custom_action(self, name: str, func: Callable, description: str = None) -> None:
        """
        Register a class method as a custom action that can be called by the LLM.
        
        Args:
            name: Name of the action (must be unique)
            func: Method reference to call when action is invoked
            description: Optional description of what the action does
        """
        self.action_manager.register_action(name, func, description)


    @property
    def utils(self) -> AgentUtils:
        """Get agent utils instance for current module and workflow context"""
        if not self.context:
            raise ValueError("No active context - utils cannot be accessed")
        if not self._utils or self._utils.module_id != self.context.module_id or self._utils.workflow != self.context.workflow:
            self._utils = AgentUtils(
                self.services.module_service,
                self.services.repo_service,
                self.context.module_id,
                self.context.workflow
            )
        return self._utils

    def get_giml(self) -> Dict[str, Dict[str, Any]]:
        """Get GIML (Generative Interface Markup Language) element schemas and descriptions"""
        return {
            "select": {
                "format": """
    <giml>
        <select id="<unique id>">
                <item description="Description of what this option means">Option text1</item>
                <item description="Description of what this second option means">Option text2</item>
                ...
        </select>
    </giml>""",
                "use": "Prompt the user with options",
                "schema": {
                    "children": {
                        "select": {
                            "attributes": ["id"],
                            "children": {
                                "item": {
                                    "attributes": ["description"],
                                    "type": "text",
                                    "multiple": True
                                }
                            }
                        }
                    }
                }
            },
            "code_diff": {
                "format": """
    <giml>
        <code file="path/to/file" id="<unique id>">
            <original>Original code block</original>
            <updated>Updated code block</updated>
        </code>
    </giml>""",
                "use": "Show code changes with original and updated versions",
                "schema": {
                    "children": {
                        "code": {
                            "attributes": ["file", "id"],
                            "children": {
                                "original": {"type": "text"},
                                "updated": {"type": "text"}
                            }
                        }
                    }
                }
            }
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

        if action_names is None:
            tools: List[EnhancedWorkflowAction] = [
                {
                    "type": "function",
                    "function": {
                        "name": action.action.name,
                        "description": action.action.description,
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
                        "name": action.action.name,
                        "description": action.action.description,
                        "parameters": action.metadata.parameters if action.metadata else {}
                    }
                }
                for action in workflow_data.actions
                if action.action.name in action_names
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
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
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


        self.history_manager.add_to_history(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            message_type=message_type,
            tool_calls=tool_calls if tool_calls else None,
            session_id=self.context.session_id
        )

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get complete chat history"""
        if not self.context:
            raise ValueError("No active context")
            
        chat_history = self.history_manager.get_chat_history(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            session_id=self.context.session_id
        )
        # Select only few attributes: role, content(optional), tool_call_id(optional), name(optional), tool calls(optional)
        formatted_history = []
        for msg in chat_history:
            formatted_msg = {k: v for k, v in msg.items() if k in ["role", "content", "tool_call_id", "name", "tool_calls"]}
            formatted_history.append(formatted_msg)
        return formatted_history

    def get_last_assistant_message(self, return_json: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the last message from the assistant in chat history
        
        Args:
            return_json: Whether to return tool calls as JSON rather than model instances
            
        Returns:
            Last assistant message as a dictionary, or None if no assistant messages found
            
        Raises:
            ValueError: If no active context
        """
        if not self.context:
            raise ValueError("No active context")
            
        return self.history_manager.get_last_assistant_message(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            session_id=self.context.session_id,
            return_json=return_json
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
                name=action_name
            )

            result = self.services.workflow_service.execute_workflow_action(
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
        save_messages: bool = True,
        process_response: bool = True,
        include_history: bool = True,
        **kwargs
    ):
        """Wrapper for model service chat completion that handles tools and history"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Get current chat history
            history = []
            if include_history:
                history = self.get_chat_history()

            # Always include system message first if we have one
            all_messages = []
            if self.system_prompt:
                all_messages.append({"role": "system", "content": self.system_prompt})

            if save_messages:
                for message in messages:
                    # Add user message to history
                    self.add_to_history(message["role"], message["content"])
            
            # Add history and new messages
            all_messages.extend(history + messages)

            logger.debug(f"Chat completion messages: {all_messages}")
            logger.debug(f"Chat completion tools: {self.tools}")
            
            # Execute chat completion with current tools
            response = await self.services.model_service.chat_completion(
                messages=all_messages,
                stream=stream,
                tools=self.tools if self.tools else None,
                tool_choice=tool_choice if self.tools else None,
                **kwargs
            )
            logger.debug(f"Chat completion response: {response}")

            if process_response:
                # Add response to history
                # check if response has tool calls
                assistant_message = response.choices[0].message
                
                if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                    # Add assistant message with tool calls info
                    self.add_to_history(
                        "assistant",
                        None,
                        message_type="tool_calls",
                        tool_calls=assistant_message.tool_calls
                    )

                    for tool_call in assistant_message.tool_calls:
                        try:
                            # Parse parameters
                            parameters = json.loads(tool_call.function.arguments)

                            # Execute the workflow action
                            result = await self.execute_workflow_action(
                                tool_call.function.name,
                                parameters
                            )

                            # Add to history with tool call ID
                            self.add_to_history(
                                role="tool",
                                content=json.dumps(result),
                                message_type="tool_result",
                                tool_call_id=tool_call.id,
                                tool_name=tool_call.function.name
                            )

                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"Error executing tool {tool_call.function.name}: {error_msg}")










                elif assistant_message.content:
                    # Add regular assistant message to history
                   self.add_to_history("assistant", assistant_message.content)

            









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

            # Get responses
            responses = self.get_response_values(context.user_input)

            logger.debug(f"Responses: {responses}")
            
            # Process workflow
            result = await self.process_workflow(context, workflow_data, responses)

            return result
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise
        finally:
            self.context = None  # Clear context


    def get_response_values(self, response_text: str) -> Optional[List[GimlResponse]]:
        """
        Extract GIML elements from last assistant message and match with responses
        
        Args:
            response_text: Text containing responses in GIML format
                Expected format:
                <giml>
                    <responses>
                        <response id="corresponding-id" value="Yes"/>
                    </responses>
                </giml>
                        
        Returns:
            List of GimlResponse objects containing:
            - id: ID of the GIML element
            - giml_type: Type of GIML element (select, code_diff, etc)
            - response_value: User's response value if provided
            - structured_giml: Full GIML structure as dictionary

        Example:
            For assistant message with multiple GIML blocks:
                Some text here
                <giml>
                    <label id="q1">First question</label>
                    <select id="s1">
                        <item description="desc1">Yes</item>
                        <item description="desc2">No</item>
                    </select>
                </giml>
                More text here
                <giml>
                    <label id="q2">Second question</label>
                    <select id="s2">
                        <item description="desc3">Option A</item>
                        <item description="desc4">Option B</item>
                    </select>
                </giml>
        """
        try:
            # Parse response GIML
            response_root = ET.fromstring(response_text)
            if response_root.tag != 'giml':
                return None

            # Get all response id/value pairs
            responses = {}
            for resp in response_root.findall(".//response"):
                resp_id = resp.get("id")
                resp_value = resp.get("value")
                if resp_id and resp_value:
                    responses[resp_id] = resp_value

            # Get assistant message
            message = self.get_last_assistant_message()
            if not message or 'content' not in message:
                return None

            result = []
            
            # Find all GIML blocks in the message
            message_content = message['content']
            giml_blocks = re.findall(r'<giml>.*?</giml>', message_content, re.DOTALL)
            
            for giml_block in giml_blocks:
                try:
                    # Parse each GIML block
                    giml_root = ET.fromstring(giml_block)
                    giml_dict = xmltodict.parse(giml_block)

                    # Check each GIML type we support
                    for giml_type in self.get_giml().keys():
                        for elem in giml_root.findall(f".//{giml_type}"):
                            elem_id = elem.get("id")
                            if elem_id:
                                result.append(GimlResponse(
                                    id=elem_id,
                                    giml_type=giml_type,
                                    response_value=responses.get(elem_id),
                                    structured_giml=giml_dict
                                ))

                except ET.ParseError:
                    logger.warning(f"Failed to parse GIML block: {giml_block}")
                    continue

            return result if result else None

        except ET.ParseError:
            return None
        except Exception as e:
            logger.error(f"Error processing GIML: {str(e)}")
            return None


    def get_store(self, collection: str) -> Optional[str]:
        """Get a stored value by key"""
        if not self.context:
            raise ValueError("No active context")
        return   WorkflowStoreService(
        storeInfo=WorkflowStoreInfo(
            module_id=self.context.module_id,
            workflow=self.context.workflow,
            collection=collection
        )
    )

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type identifier"""
        pass

    @abstractmethod
    async def   process_workflow(
        self,
        context: AgentContext,
        workflow_data: WorkflowMetadataResult,
        responses: Optional[List[GimlResponse]] = None
    ) -> Dict[str, Any]:
        """Process a workflow request"""
        pass
