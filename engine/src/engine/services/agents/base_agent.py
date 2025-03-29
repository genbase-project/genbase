from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, TypedDict, Union, final
import json
import uuid
import xml.etree.ElementTree as ET
from pydantic import BaseModel, field_validator, validator
import xmltodict
from litellm import ChatCompletionMessageToolCall, Choices
from engine.services.agents.generative_elements import get_element_format_documentation
from engine.services.core.kit import KitConfig
from engine.services.execution.action import FunctionMetadata
from engine.services.execution.internal_actions import InternalActionManager
from engine.services.execution.model import ModelService, ResponseType
from engine.services.execution.state import StateService
from engine.services.execution.profile import (
    FullProfileAction,
    ProfileExecutionResult,
    ProfileService,
    ProfileMetadataResult,
    ActionInfo
)
from engine.services.agents.chat_history import ChatHistoryManager
from engine.services.core.module import ModuleService, RelationType
from engine.services.execution.profile_store import ProfileStoreInfo, ProfileStoreRecord, ProfileStoreService
from engine.services.storage.repository import RepoService
from engine.services.agents.agent_utils import AgentUtils
from loguru import logger
from dataclasses import dataclass
from typing import Optional, List, Dict

from litellm import ModelResponse

from dataclasses import dataclass
from typing import Optional, List, Union, Literal




@dataclass
class AgentServices:
    """Essential services required by all agents"""
    model_service: ModelService     # For LLM interactions
    profile_service: ProfileService  # For profile execution
    module_service: ModuleService   # For module management
    state_service: StateService     # For agent state management
    repo_service: RepoService       # For repository operations



IncludeType = Union[Literal["all", "none"], List[str]]
TModel = TypeVar('TModel', bound=BaseModel)

class IncludeOptions(BaseModel):
    provided_actions: bool = False
    elements: IncludeType = "all"
    actions: IncludeType = "all"
    
    @field_validator('elements', 'actions')
    @classmethod
    def validate_include_type(cls, value, info):
        field_name = info.field_name
        if isinstance(value, str) and value not in ("all", "none"):
            raise ValueError(
                f"Invalid value for '{field_name}': '{value}'. "
                f"Must be 'all', 'none', or a list of strings."
            )
        elif not isinstance(value, str) and not isinstance(value, list):
            raise TypeError(
                f"Invalid type for '{field_name}': {type(value)}. "
                f"Must be 'str' ('all' or 'none') or 'list'."
            )
        elif isinstance(value, list) and not all(isinstance(item, str) for item in value):
            raise TypeError(
                f"Invalid type within '{field_name}' list. "
                f"All items in the list must be strings."
            )
        return value



@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    profile: str
    user_input: str
    session_id: Optional[str] = None

class BaseAgent(ABC):
    """Next generation base agent with core functionality"""
    
    def __init__(self, services: AgentServices):
        """Initialize base agent with required services"""
        self.services = services
        self.history_manager = ChatHistoryManager()
        self.context: Optional[AgentContext] = None
        self.actions: List[Dict[str, Any]] = []
        self.system_prompt: Optional[str] = None
        self._utils: Optional[AgentUtils] = None

        self.module_action_map: Dict[str, FullProfileAction] = {}


        # Initialize the custom action manager
        self.action_manager = InternalActionManager()




    @property
    def utils(self) -> AgentUtils:
        """Get agent utils instance for current module and profile context"""
        if not self.context:
            raise ValueError("No active context - utils cannot be accessed")
        if not self._utils or self._utils.module_id != self.context.module_id or self._utils.profile != self.context.profile:
            self._utils = AgentUtils(
                self.services.module_service,
                self.services.repo_service,
                self.context.module_id,
                self.context.profile
            )
        return self._utils



    async def set_context(
        self,
        agent_instructions: str = None,
        internal_actions: Optional[Dict[str, Callable]] = None,
        include: IncludeOptions = IncludeOptions(
            provided_actions=False,
            elements="all",
            actions="all",
        )

    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Build system prompt with selected actions as tools
        
        Args:
            agent_instructions: Optional agent-specific instructions
            actions: List of action names to include, or None for all actions
            include: Whether to include provided actions and GIML elements
            
        Returns:
            Tuple of (system prompt, list of tools)
        """
        if not self.context:
            raise ValueError("No active context")
            
        parts: Dict[str, str] = {"Agent Instructions": agent_instructions}
        tools = []

        # Get Profile metadata
        profile_data: ProfileMetadataResult = self.services.profile_service.get_profile_metadata(
            self.context.module_id,
            self.context.profile,
            with_provided=include.provided_actions
        )

        # Clear existing custom actions if we're passed new ones
        logger.info(f"Setting context with internal actions: {internal_actions}")
        if internal_actions is not None:
            self.action_manager.register_actions(internal_actions)

        # Get profile actions
        profile_actions = []


        if include.actions == "none":
            profile_actions = []        

        elif include.actions == "all":
            # Include all profile actions
            profile_actions = [
                {
                    "type": "function",
                    "function": {
                        "name": action.action.name,
                        "description": action.action.description,
                        "parameters": action.metadata.parameters if action.metadata else {}
                    }
                }
                for action in profile_data.actions
            ]
            for action in profile_data.actions:
                self.module_action_map[action.action.name] = action
        else:
            # Filter profile actions by name
            profile_actions = [
                {
                    "type": "function",
                    "function": {
                        "name": action.action.name,
                        "description": action.action.description,
                        "parameters": action.metadata.parameters if action.metadata else {}
                    }
                }
                for action in profile_data.actions
                if action.action.name in include.actions
            ]
            for action in profile_data.actions:
                if action.action.name in include.actions:
                    self.module_action_map[action.action.name] = action
        
        # Add profile actions to tools
        tools.extend(profile_actions)
        
        # Add custom actions from the action manager

        internal_action_tools = self.action_manager.get_tool_definitions(include.actions)
        logger.info(f"Internal action tools: {internal_action_tools}")
        tools.extend(internal_action_tools)

        # Add tool descriptions to prompt
        profile_tool_descriptions = []
        for tool in tools:
            profile_tool_descriptions.append(
                f"- {tool['function']['name']}: {tool['function']['description']}"
            )

        if profile_tool_descriptions:
            parts["Available tools"]= "\n".join(profile_tool_descriptions)

        element_format_docs = get_element_format_documentation(include.elements)
        if element_format_docs:
            parts["Generative Elements Formatting"] = element_format_docs
            logger.info(f"Included documentation for element formats: {include.elements}")


        final_instruction = ""
        for key, value in parts.items():
            if value:
                final_instruction += f"\n\n##{key}:\n{value}"
            
        self.actions = tools

        logger.info(f"Set context with actions: {tools}")
        self.system_prompt = final_instruction
        return final_instruction, tools
        
    async def run_action(
        self,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a profile action or custom internal action"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Check if this is a custom internal action first
            if self.action_manager.has_action(action_name):
                # Execute internal action
                return await self.action_manager.execute_action(action_name, parameters)
            
            # Otherwise, execute as a normal profile action
            action_info = ActionInfo(
                module_id=(self.module_action_map[action_name]).module_id or self.context.module_id,
                profile=self.context.profile,
                name=action_name
            )

            result = self.services.profile_service.execute_profile_action(
                action_info=action_info,
                parameters=parameters,
                with_provided=self.module_action_map[action_name].is_provided
            )

            return result
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            raise


    def add_message(
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
            profile=self.context.profile,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            message_type=message_type,
            tool_calls=tool_calls if tool_calls else None,
            session_id=self.context.session_id
        )

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get complete chat history"""
        if not self.context:
            raise ValueError("No active context")
            
        chat_history = self.history_manager.get_chat_history(
            module_id=self.context.module_id,
            profile=self.context.profile,
            session_id=self.context.session_id
        )
        # Select only few attributes: role, content(optional), tool_call_id(optional), name(optional), tool calls(optional)
        formatted_history = []
        for msg in chat_history:
            formatted_msg = {k: v for k, v in msg.items() if k in ["role", "content", "tool_call_id", "name", "tool_calls"]}
            formatted_history.append(formatted_msg)
        return formatted_history


    def _get_last_assistant_message(self, return_json: bool = False) -> Optional[Dict[str, Any]]:
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
            
        return self.history_manager.get_last_message(
            module_id=self.context.module_id,
            profile=self.context.profile,
            session_id=self.context.session_id,
            return_json=return_json
        )


    async def create(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        action_choice: Optional[str] = "auto",
        save_messages: bool = True,
        run_actions: bool = True,
        use_history: bool = True,
        **kwargs
    ):
        """Wrapper for model service chat completion that handles tools and history"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Get current chat history
            history = []
            if use_history:
                history = self.get_messages()

            # Always include system message first if we have one
            all_messages = []
            if self.system_prompt:
                all_messages.append({"role": "system", "content": self.system_prompt})

            if save_messages:
                for message in messages:
                    # Add user message to history
                    self.add_message(message["role"], message["content"])
            
            # Add history and new messages
            all_messages.extend(history + messages)

            logger.debug(f"Chat completion messages: {all_messages}")
            logger.debug(f"Chat completion tools: {self.actions}")
            
            # Execute chat completion with current tools
            response = await self.services.model_service.chat_completion(
                messages=all_messages,
                stream=stream,
                tools=self.actions if self.actions else None,
                tool_choice=action_choice if self.actions else None,
                **kwargs
            )
            logger.debug(f"Chat completion response: {response}")

            if run_actions:
                # Add response to history
                # check if response has tool calls
                assistant_message = response.choices[0].message
                
                if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                    # Add assistant message with tool calls info
                    self.add_message(
                        "assistant",
                        None,
                        message_type="tool_calls",
                        tool_calls=assistant_message.tool_calls
                    )

                    for tool_call in assistant_message.tool_calls:
                        try:
                            # Parse parameters
                            parameters = json.loads(tool_call.function.arguments)


                            # Execute the profile action
                            result = await self.run_action(
                                tool_call.function.name,
                                parameters
                            )

                            # Add to history with tool call ID
                            self.add_message(
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
                   self.add_message("assistant", assistant_message.content)

            






            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise



    async def create_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[ResponseType],
        save_messages: bool = True,
        use_history: bool = True,
        **kwargs
    ) -> Tuple[ResponseType, ModelResponse]:
        """Wrapper for model service structured output that handles tools and history"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Get current chat history
            history = []
            if use_history:
                history = self.get_messages()

            # Always include system message first if we have one
            all_messages = []
            if self.system_prompt:
                all_messages.append({"role": "system", "content": self.system_prompt})

            if save_messages:
                for message in messages:
                    # Add user message to history
                    self.add_message(message["role"], message["content"])
            
            # Add history and new messages
            all_messages.extend(history + messages)

            logger.debug(f"Structured chat completion messages: {all_messages}")
            logger.debug(f"Structured chat completion tools: {self.actions}")
            
            # Execute structured chat completion with current tools
            structured_response, raw_response =  self.services.model_service.structured_output(
                messages=all_messages,
                response_model=response_model,
                **kwargs
            )

            logger.debug(f"Structured chat completion response: {raw_response}")

            if save_messages:
                # Add assistant message to history
                assistant_message = raw_response.choices[0].message
                if assistant_message.content:
                    self.add_message("assistant", assistant_message.content)

            return structured_response, raw_response

        except Exception as e:
            logger.error(f"Structured chat completion failed: {str(e)}")
            raise




    async def handle_request(self, context: AgentContext) -> Dict[str, Any]:
        """Process an agent request"""
        try:
            self.context = context
            # Get profile metadata
            profile_data: ProfileMetadataResult =  self.services.profile_service.get_profile_metadata(
                context.module_id,
                context.profile
            )

            
            # Process profile
            result = await self.process_request(context, profile_data)

            return result
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise
        finally:
            self.context = None  # Clear context



    def get_store(self, collection: str) -> Optional[str]:
        """Get a stored value by key"""
        if not self.context:
            raise ValueError("No active context")
        return   ProfileStoreService(
        storeInfo=ProfileStoreInfo(
            module_id=self.context.module_id,
            profile=self.context.profile,
            collection=collection
        )
    )

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type identifier"""
        pass

    @abstractmethod
    async def   process_request(
        self,
        context: AgentContext,
        profile_data: ProfileMetadataResult
    ) -> Dict[str, Any]:
        """Process a profile request"""
        pass
