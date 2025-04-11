from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from functools import wraps
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
from engine.services.execution.tool import FunctionMetadata
from engine.services.execution.internal_tools import InternalToolManager
from engine.services.execution.model import ModelService, ResponseType
from engine.services.execution.state import StateService
from engine.services.execution.profile import (
    FullProfileTool,
    ProfileExecutionResult,
    ProfileService,
    ProfileMetadataResult,
    ToolInfo
)
from engine.services.agents.chat_history import ChatHistoryManager
from engine.services.core.module import ModuleService
from engine.services.execution.profile_store import ProfileStoreInfo, ProfileStoreRecord, ProfileStoreService
from engine.services.storage.repository import RepoService
from engine.services.agents.agent_utils import AgentUtils
from loguru import logger
from dataclasses import dataclass
from typing import Optional, List, Dict

from litellm import ModelResponse

from dataclasses import dataclass
from typing import Optional, List, Union, Literal


# Note: Agents should only import from BaseAgent

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
    provided_tools: bool = False
    elements: IncludeType = "all"
    tools: IncludeType = "all"
    
    @field_validator('elements', 'tools')
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
        self.tools: List[Dict[str, Any]] = []
        self.system_prompt: Optional[str] = None
        self._utils: Optional[AgentUtils] = None

        self.current_model = None

        self.module_tool_map: Dict[str, FullProfileTool] = {}


        # Initialize the custom tool manager
        self.tool_manager = InternalToolManager()




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
        include: IncludeOptions = IncludeOptions(
            provided_tools=False,
            elements="all",
            tools="all",
        ),
        model: Optional[str] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Build system prompt with selected tools as tools
        
        Args:
            agent_instructions: Optional agent-specific instructions
            tools: List of tool names to include, or None for all tools
            include: Whether to include provided tools and elements
            
        Returns:
            Tuple of (system prompt, list of tools)
        """
        if not self.context:
            raise ValueError("No active context")
        

        self.current_model = model or self.services.model_service.get_current_model()
            
        parts: Dict[str, str] = {"Agent Instructions": agent_instructions}
        tools = []

        # Get Profile metadata
        profile_data: ProfileMetadataResult = self.services.profile_service.get_profile_metadata(
            self.context.module_id,
            self.context.profile,
            with_provided=include.provided_tools
        )

        internal_tools = collect_tools(self)

        logger.info(f"Setting context with internal tools: {internal_tools}")
        if internal_tools is not None:
            self.tool_manager.register_tools(internal_tools)

     
        profile_tools = []


        if include.tools == "none":
            profile_tools = []        

        elif include.tools == "all":
            profile_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.tool.name,
                        "description": tool.tool.description,
                        "parameters": tool.metadata.parameters if tool.metadata else {}
                    }
                }
                for tool in profile_data.tools
            ]
            for tool in profile_data.tools:
                self.module_tool_map[tool.tool.name] = tool
        else:
            # Filter profile tools by name
            profile_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.tool.name,
                        "description": tool.tool.description,
                        "parameters": tool.metadata.parameters if tool.metadata else {}
                    }
                }
                for tool in profile_data.tools
                if tool.tool.name in include.tools
            ]
            for tool in profile_data.tools:
                if tool.tool.name in include.tools:
                    self.module_tool_map[tool.tool.name] = tool
        
        # Add profile tools to tools
        tools.extend(profile_tools)
        
        # Add custom tools from the tool manager

        internal_tools = self.tool_manager.get_tool_definitions(include.tools)
        logger.info(f"Internal tools: {internal_tools}")
        tools.extend(internal_tools)

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
            
        self.tools = tools

        logger.info(f"Set context with tools: {tools}")
        self.system_prompt = final_instruction
        return final_instruction, tools
        
    async def run_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a profile tool or custom internal tool"""
        try:
            if not self.context:
                raise ValueError("No active context")

            # Check if this is a custom internal tool first
            if self.tool_manager.has_tool(tool_name):
                # Execute internal tool
                return await self.tool_manager.execute_tool(tool_name, parameters)
            
            # Otherwise, execute as a normal profile tool
            tool_info = ToolInfo(
                module_id=(self.module_tool_map[tool_name]).module_id or self.context.module_id,
                profile=self.context.profile,
                name=tool_name
            )

            result = self.services.profile_service.execute_profile_tool(
                tool_info=tool_info,
                parameters=parameters,
                with_provided=self.module_tool_map[tool_name].is_provided
            )

            return result
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
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
        tool_choice: Optional[str] = "auto",
        save_messages: bool = True,
        run_tools: bool = True,
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
            logger.debug(f"Chat completion tools: {self.tools}")
            
            # Execute chat completion with current tools
            response = await self.services.model_service.chat_completion(
                messages=all_messages,
                stream=stream,
                tools=self.tools if self.tools else None,
                tool_choice=tool_choice if self.tools else None,
                model=self.current_model,
                **kwargs
            )
            logger.debug(f"Chat completion response: {response}")

            if run_tools:
                assistant_message = response.choices[0].message
                
                if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                    # Variables to track successful tool calls
                    successful_tool_calls = []
                    successful_tool_results = []
                    
                    # Execute all tool calls and track successful ones
                    for tool_call in assistant_message.tool_calls:
                        try:
                            # Parse parameters
                            parameters = json.loads(tool_call.function.arguments)

                            # Execute the profile tool
                            result = await self.run_tool(
                                tool_call.function.name,
                                parameters
                            )

                            # Store successful tool call and result for history
                            successful_tool_calls.append(tool_call)
                            successful_tool_results.append({
                                "role": "tool",
                                "content": json.dumps(result),
                                "message_type": "tool_result",
                                "tool_call_id": tool_call.id,
                                "tool_name": tool_call.function.name
                            })
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"Error executing tool {tool_call.function.name}: {error_msg}")
                    
                    # If we have successful tool calls, add them to history
                    if successful_tool_calls:
                        # Add the assistant message with tool calls first
                        self.add_message(
                            "assistant",
                            None,
                            message_type="tool_calls",
                            tool_calls=successful_tool_calls  # Only include successful tool calls
                        )
                        
                        # Then add each successful tool result
                        for result_info in successful_tool_results:
                            self.add_message(
                                role=result_info["role"],
                                content=result_info["content"],
                                message_type=result_info["message_type"],
                                tool_call_id=result_info["tool_call_id"],
                                tool_name=result_info["tool_name"]
                            )
                    else:
                        # If no successful tool calls, just add the assistant message content
                        # or an error message if content is None
                        content = assistant_message.content or "Failed to execute tool calls."
                        self.add_message("assistant", content)
                
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
            logger.debug(f"Structured chat completion tools: {self.tools}")
            
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



    def get_store(self, collection: str) -> Optional[ProfileStoreService]:
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















def tool(func):
    """
    Simple decorator to mark methods as agent tools.
    The method name becomes the tool name, and the docstring becomes the description.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Just mark this method as an tool
    wrapper._is_tool = True
    return wrapper


def collect_tools(instance) -> Dict[str, Callable]:
    """
    Collect all methods marked as tools from an instance
    
    Returns:
        Dictionary mapping tool names to method references
    """
    tools = {}
    
    # Iterate through all attributes of the instance
    for attr_name in dir(instance):
        if attr_name.startswith('__'):
            continue
            
        attr = getattr(instance, attr_name)
        
        # Check if this is a marked tool
        if callable(attr) and hasattr(attr, '_is_tool'):
            # Use method name as tool name
            tools[attr_name] = attr
    
    return tools