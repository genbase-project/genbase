# engine/src/engine/services/platform_rpyc_service.py

from pathlib import Path
import rpyc
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union, Type
from pydantic import BaseModel
import rpyc.utils
import rpyc.utils.classic
from sqlalchemy import select

from engine.const import SUPPORTED_CONTENT_TYPES_DEFINITION, SUPPORTED_MIME_TYPES_LIST
from engine.db.session import SessionLocal
from engine.services.agents.types import AgentServices
from engine.services.agents.chat_history import ChatHistoryManager
from engine.services.execution.profile import ToolInfo, ProfileMetadataResult
from engine.services.execution.profile_store import ProfileStoreInfo, ProfileStoreService, ProfileStoreFilter, ProfileStoreRecord
from engine.services.agents.agent_utils import AgentUtils
from engine.db.models import Module, ModuleProvide, ProvideType
from engine.utils.readable_uid import generate_readable_uid
from engine.utils.file import is_safe_path
from engine.services.execution.model import ResponseType # Import ResponseType

from litellm import ModelResponse, ChatCompletionMessageToolCall

from loguru import logger













def _safe_serialize_for_json(obj):
    """Convert any non-JSON serializable objects to strings or representative types."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [_safe_serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): _safe_serialize_for_json(v) for k, v in obj.items()}
    elif hasattr(obj, 'model_dump') and callable(obj.model_dump):
        # Handle Pydantic models
        return _safe_serialize_for_json(obj.model_dump(mode='json'))
    elif hasattr(obj, 'dict') and callable(obj.dict):
        # Handle older Pydantic models
        return _safe_serialize_for_json(obj.dict())
    elif hasattr(obj, 'toJSON') and callable(obj.toJSON):
        # Handle custom JSON conversion
        return _safe_serialize_for_json(obj.toJSON())
    else:
        # Convert anything else to string
        return str(obj)






class PlatformRPyCService(rpyc.Service):
    """
    RPyC Service running in the main engine, exposing platform functionalities
    to containerized agents.
    """
    ALIASES = ["agent_services", "history_manager"]

    def __init__(self, services: AgentServices):
        if not isinstance(services, AgentServices):
            raise TypeError("PlatformRPyCService requires an instance of AgentServices")
        self.agent_services = services
        self.history_manager = ChatHistoryManager()

        logger.info("PlatformRPyCService initialized.")
        super().__init__()

    def on_connect(self, conn):
        logger.info(f"RPyC client connected: {conn}")
        # Configure connection safety settings
    # Configure connection safety settings
        conn._config["allow_public_attrs"] = True  # Change to True
        conn._config["allow_pickle"] = True       # Change to True for LiteLLM compatibility
        conn._config["allow_setattr"] = False
        conn._config["allow_delattr"] = False
        conn._config["allow_all_attrs"] = True    # Change to True



    def on_disconnect(self, conn):
        logger.info(f"RPyC client disconnected: {conn}")

    def _run_async(self, coro):
        """Helper to run async coroutines from sync RPyC handlers."""
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=300) # 5 minute timeout
        except RuntimeError: # No loop running in current thread
            return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error running async task in RPyC service: {e}", exc_info=True)
            raise ValueError(f"Async task execution failed: {e}") from e # Propagate as standard error

    # --- Chat History ---
    def exposed_add_message(self, module_id: str, profile: str, session_id: str, role: str,
                            content: Optional[str], message_type: str = "text",
                            tool_calls_serializable: Optional[List[Dict]] = None,
                            tool_call_id: Optional[str] = None, name: Optional[str] = None):
        logger.debug(f"RPyC exposed_add_message call: {module_id}/{profile}/{session_id} Role: {role}")
        try:
            # Convert netref objects to local objects using RPyC utilities
            tool_calls_serializable_local = rpyc.utils.classic.obtain(tool_calls_serializable) if tool_calls_serializable else None
            
            # Now validate with the local objects
            tool_calls = [ChatCompletionMessageToolCall.model_validate(tc) for tc in tool_calls_serializable_local] if tool_calls_serializable_local else None
            
            self.history_manager.add_to_history(
                module_id=module_id, profile=profile, session_id=session_id, role=role,
                content=content, message_type=message_type, tool_calls=tool_calls,
                tool_call_id=tool_call_id, name=name
            )
        except Exception as e:
            logger.error(f"Error in exposed_add_message: {e}", exc_info=True)
            raise ValueError(f"Failed to add to history: {e}")

    def exposed_get_messages( self, module_id: str, profile: str, session_id: str ) -> List[Dict[str, Any]]:
        logger.debug(f"RPyC exposed_get_messages call: {module_id}/{profile}/{session_id}")
        try:
            # return_json=True ensures serializable output
            return self.history_manager.get_chat_history(
                module_id=module_id, profile=profile, session_id=session_id, return_json=True
            )
        except Exception as e:
            logger.error(f"Error in exposed_get_messages: {e}", exc_info=True)
            raise ValueError(f"Failed to get messages: {e}")







        
        # --- Model Service ---
    def exposed_chat_completion(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None,
        stream: bool = False, tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, str]]] = None, **kwargs
    ) -> Dict[str, Any]:
        if stream:
            logger.warning("Streaming requested via RPyC, performing non-streamed call.")
            stream = False  # Override stream flag for RPyC

        effective_model = model or self.agent_services.model_service.get_current_model()
        logger.debug(f"RPyC exposed_chat_completion call. Model: {effective_model}")
        

        # # Add this debugging before calling the model service
        for i, msg in enumerate(messages):
            logger.debug(f"Message {i} type: {type(msg)}")
            if isinstance(msg, dict):
                for k, v in msg.items():
                    logger.debug(f"  Key '{k}' has type: {type(v)}")
        try:
            # Use custom serialization to ensure JSON compatibility
            serialized_messages = _safe_serialize_for_json(messages)
            serialized_tools = _safe_serialize_for_json(tools) if tools else None
            serialized_kwargs = _safe_serialize_for_json(kwargs)
            
            # Print debug info for troubleshooting
            logger.debug(f"Messages serialized: {len(serialized_messages)} items")
            logger.debug(f"Tools serialized: {serialized_tools is not None}")
            
            # Call the model service with serialized data
            coro = self.agent_services.model_service.chat_completion(
                model=effective_model, 
                messages=serialized_messages,
                stream=stream,
                tools=serialized_tools, 
                tool_choice=tool_choice,
                **serialized_kwargs
            )
            
            response: ModelResponse = self._run_async(coro)

            logger.debug(f"Chat completion response: {response}")
            return response.model_dump(mode='json')  # Return dict
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in exposed_chat_completion: {error_msg}", exc_info=True)
            raise ValueError(f"Chat completion failed: {error_msg}")


    def exposed_structured_output( self, messages: List[Dict[str, Any]], response_model_name: str,
                                   response_model_module: str, model: Optional[str] = None, **kwargs
                                 ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        effective_model = model or self.agent_services.model_service.get_current_model()
        logger.debug(f"RPyC exposed_structured_output call. Model: {effective_model}, Response Model: {response_model_module}.{response_model_name}")
        try:
            # Dynamically import the Pydantic model (requires careful security considerations in production)
            try:
                module = __import__(response_model_module, fromlist=[response_model_name])
                pydantic_model_class: Type[BaseModel] = getattr(module, response_model_name)
                if not issubclass(pydantic_model_class, BaseModel):
                     raise TypeError(f"{response_model_name} is not a Pydantic BaseModel")
            except (ImportError, AttributeError, TypeError) as ie:
                 logger.error(f"Failed to import/validate response model '{response_model_module}.{response_model_name}': {ie}")
                 raise ValueError(f"Invalid response model specified: {ie}") from ie

            coro = self.agent_services.model_service.structured_output(
                model=effective_model, messages=messages, response_model=pydantic_model_class, **kwargs
            )
            structured_response: BaseModel
            raw_response: ModelResponse
            structured_response, raw_response = self._run_async(coro)
            return structured_response.model_dump(mode='json'), raw_response.model_dump(mode='json')
        except Exception as e:
            logger.error(f"Error in exposed_structured_output: {e}", exc_info=True)
            raise ValueError(f"Structured output failed: {e}")


    def exposed_get_profile_metadata( self, module_id: str, profile: str, with_provided: bool = False ) -> Dict[str, Any]:
        logger.debug(f"RPyC exposed_get_profile_metadata call: {module_id}/{profile}")
        try:
            # ProfileService.get_profile_metadata is synchronous
            metadata: ProfileMetadataResult = self.agent_services.profile_service.get_profile_metadata(
                module_id=module_id, profile=profile, with_provided=with_provided
            )
            return metadata.model_dump(mode='json') # Return dict
        except Exception as e:
            logger.error(f"Error in exposed_get_profile_metadata: {e}", exc_info=True)
            raise ValueError(f"Failed to get profile metadata: {e}")

    # --- AgentUtils Wrappers ---
    def _get_agent_utils(self, module_id: str, profile: str) -> AgentUtils:
        """Helper to get utils instance dynamically based on context."""
        return AgentUtils(
            self.agent_services.module_service,
            self.agent_services.repo_service,
            module_id,
            profile
        )

    def exposed_read_file(self, module_id: str, profile: str, relative_path: str) -> Optional[str]:
        logger.debug(f"RPyC exposed_read_file call: {module_id}/{profile} Path: {relative_path}")
        try:
            return self._get_agent_utils(module_id, profile).read_file(relative_path)
        except Exception as e:
            logger.error(f"Error in exposed_read_file '{relative_path}': {e}", exc_info=True)
            raise ValueError(f"Failed to read file '{relative_path}': {e}")

    def exposed_write_file(self, module_id: str, profile: str, relative_path: str, content: str) -> bool:
        logger.debug(f"RPyC exposed_write_file call: {module_id}/{profile} Path: {relative_path}")
        try:
            return self._get_agent_utils(module_id, profile).write_file(relative_path, content)
        except Exception as e:
            logger.error(f"Error in exposed_write_file '{relative_path}': {e}", exc_info=True)
            raise ValueError(f"Failed to write file '{relative_path}': {e}")

    def exposed_list_files(self, module_id: str, profile: str, relative_path: str = "") -> List[str]:
        logger.debug(f"RPyC exposed_list_files call: {module_id}/{profile} Path: {relative_path}")
        try:
            paths = self._get_agent_utils(module_id, profile).list_files(relative_path)
            return [str(p) for p in paths] # Return strings
        except Exception as e:
            logger.error(f"Error in exposed_list_files '{relative_path}': {e}", exc_info=True)
            raise ValueError(f"Failed to list files '{relative_path}': {e}")

    def exposed_get_repo_tree(self, module_id: str, profile: str, path_str: Optional[str] = None) -> str:
        logger.debug(f"RPyC exposed_get_repo_tree call: {module_id}/{profile} Path: {path_str}")
        try:
            path_obj = None
            if path_str:
                from pathlib import Path
                path_obj = Path(path_str)
            return self._get_agent_utils(module_id, profile).get_repo_tree(path_obj)
        except Exception as e:
            logger.error(f"Error in exposed_get_repo_tree '{path_str}': {e}", exc_info=True)
            raise ValueError(f"Failed to get repo tree '{path_str}': {e}")

    # --- Profile Store ---
    def _get_profile_store_service(self, module_id: str, profile: str, collection: str) -> ProfileStoreService:
        """Helper to get ProfileStoreService instance."""
        store_info = ProfileStoreInfo(module_id=module_id, profile=profile, collection=collection)
        return ProfileStoreService(storeInfo=store_info)

    def exposed_profile_store_find(self, module_id: str, profile: str, collection: str, filter_dict: Dict) -> List[Dict]:
        logger.debug(f"RPyC exposed_profile_store_find call: {module_id}/{profile}/{collection}")
        try:
            # Ensure filter_dict is local
            filter_dict = rpyc.utils.classic.obtain(filter_dict)
            
            store_service = self._get_profile_store_service(module_id, profile, collection)
            filter_obj = ProfileStoreFilter(**filter_dict)
            coro = store_service.find(filter_obj)
            records: List[ProfileStoreRecord] = self._run_async(coro)
            import dataclasses
            return [dataclasses.asdict(r) for r in records] # Return list of dicts
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_find: {e}", exc_info=True)
            raise ValueError(f"Failed to find in profile store '{collection}': {e}")

    def exposed_profile_store_set_value(self, module_id: str, profile: str, collection: str, value: Dict) -> Dict:
        logger.debug(f"RPyC exposed_profile_store_set_value call: {module_id}/{profile}/{collection}")
        try:
            # Ensure value is local
            value = rpyc.utils.classic.obtain(value)
            
            store_service = self._get_profile_store_service(module_id, profile, collection)

            coro = store_service.set_value(value)
            record: ProfileStoreRecord = self._run_async(coro)
            import dataclasses
            return dataclasses.asdict(record) # Return dict
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_set_value: {e}", exc_info=True)
            raise ValueError(f"Failed to set value in profile store '{collection}': {e}")

    def exposed_profile_store_delete(self, module_id: str, profile: str, collection: str, filter_dict: Dict) -> int:
        logger.debug(f"RPyC exposed_profile_store_delete call: {module_id}/{profile}/{collection}")
        try:
            filter_dict = rpyc.utils.classic.obtain(filter_dict)
            store_service = self._get_profile_store_service(module_id, profile, collection)
            filter_obj = ProfileStoreFilter(**filter_dict)
            coro = store_service.delete(filter_obj)
            deleted_count = self._run_async(coro)
            return deleted_count
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_delete: {e}", exc_info=True)
            raise ValueError(f"Failed to delete from profile store '{collection}': {e}")

    def exposed_profile_store_get_by_id(self, module_id: str, profile: str, collection: str, record_id_str: str) -> Optional[Dict]:
        logger.debug(f"RPyC exposed_profile_store_get_by_id call: {module_id}/{profile}/{collection} ID: {record_id_str}")
        try:
            record_uuid = uuid.UUID(record_id_str)
            store_service = self._get_profile_store_service(module_id, profile, collection)
            coro = store_service.get_by_id(record_uuid)
            record: Optional[ProfileStoreRecord] = self._run_async(coro)
            if record:
                import dataclasses
                return dataclasses.asdict(record)
            return None
        except ValueError:
             logger.error(f"Invalid UUID format received: {record_id_str}")
             raise ValueError(f"Invalid record ID format.")
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_get_by_id: {e}", exc_info=True)
            raise ValueError(f"Failed to get record by ID from profile store '{collection}': {e}")

    def exposed_profile_store_set_many(self, module_id: str, profile: str, collection: str, values: List[Dict]) -> List[Dict]:
        logger.debug(f"RPyC exposed_profile_store_set_many call: {module_id}/{profile}/{collection} Count: {len(values)}")
        try:
            values = rpyc.utils.classic.obtain(values)
            store_service = self._get_profile_store_service(module_id, profile, collection)
            coro = store_service.set_many(values)
            records: List[ProfileStoreRecord] = self._run_async(coro)
            import dataclasses
            return [dataclasses.asdict(r) for r in records] # Return list of dicts
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_set_many: {e}", exc_info=True)
            raise ValueError(f"Failed to set many values in profile store '{collection}': {e}")

    def exposed_profile_store_update(self, module_id: str, profile: str, collection: str, filter_dict: Dict, value: Dict) -> int:
        logger.debug(f"RPyC exposed_profile_store_update call: {module_id}/{profile}/{collection}")
        try:
            value = rpyc.utils.classic.obtain(value)
            filter_dict = rpyc.utils.classic.obtain(filter_dict)
            store_service = self._get_profile_store_service(module_id, profile, collection)
            filter_obj = ProfileStoreFilter(**filter_dict)
            coro = store_service.update(filter_obj, value)
            updated_count = self._run_async(coro)
            return updated_count
        except Exception as e:
            logger.error(f"Error in exposed_profile_store_update: {e}", exc_info=True)
            raise ValueError(f"Failed to update profile store '{collection}': {e}")



    def exposed_structured_output_with_schema(
        self, messages: List[Dict[str, Any]], response_model_schema: Dict[str, Any],
        model: Optional[str] = None, **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # Get local copies of all parameters
        messages = rpyc.utils.classic.obtain(messages)
        response_model_schema = rpyc.utils.classic.obtain(response_model_schema)
        kwargs = rpyc.utils.classic.obtain(kwargs)
        
        effective_model = model or self.agent_services.model_service.get_current_model()

        logger.debug(f"RPyC exposed_structured_output_with_schema call. Model: {effective_model}")
        try:
            # Create a dynamic Pydantic model from the provided schema
            from pydantic import create_model
            from pydantic.json_schema import model_json_schema
            
            # Create a dynamic model using the provided schema
            DynamicModel = create_model('DynamicResponseModel', **{
                '__annotations__': {}, 
                '__config__': type('Config', (), {'extra': 'allow'})
            })
            # We'll patch its json schema method to return our provided schema
            DynamicModel.__pydantic_core_schema__ = response_model_schema
            
            # Run structured_output with the dynamic model
            coro = self.agent_services.model_service.structured_output(
                model=effective_model, messages=messages, response_model=DynamicModel, **kwargs
            )
            structured_response, raw_response = self._run_async(coro)
            
            # Return as dicts for RPyC serialization
            return structured_response.model_dump(mode='json'), raw_response.model_dump(mode='json')
        except Exception as e:
            logger.error(f"Error in exposed_structured_output_with_schema: {e}", exc_info=True)
            raise ValueError(f"Structured output with schema failed: {e}")











    def exposed_get_provided_tools_schema(self, module_id: str, profile: str) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compliant schema for tools provided by other modules to this module.
        
        Args:
            module_id: The module requesting tools
            profile: The profile requesting tools
            
        Returns:
            List of tool schemas in OpenAI function calling format
        """
        logger.debug(f"Getting provided tools schema for {module_id}/{profile}")
        
        try:
            # Query the module_provides table to find modules providing tools to this module
            with SessionLocal() as db:
                # Get provider modules from the ModuleProvide table where this module is the receiver
                stmt = select(ModuleProvide).where(
                    ModuleProvide.receiver_id == module_id,
                    ModuleProvide.resource_type == ProvideType.TOOL
                ).join(
                    Module, 
                    ModuleProvide.provider_id == Module.module_id
                )
                
                providers = db.execute(stmt).scalars().all()
                
                # Collect all tool schemas
                all_tools = []
                
                logger.debug(f"Found {len(providers)} providers for tools.")
                for provider in providers:
                    logger.debug(f"Processing provider: {provider.provider_id}")
                    provider_id = provider.provider_id
                    
                    try:
                        # Get the kit config to find which profiles have provided tools
                        kit_config = self.agent_services.module_service.get_module_kit_config(provider_id)
                        
                        # Check the "provide" section to see which tools are offered
                        provided_tools = kit_config.provide.tools if hasattr(kit_config.provide, "tools") else []
                        
                        logger.debug(f"Provider {provider_id} offers {len(provided_tools)} tools.")
                        # Group tools by profile
                        profile_tools = {}
                        for tool in provided_tools:
                            tool_profile = tool.profile
                            if tool_profile not in profile_tools:
                                profile_tools[tool_profile] = []
                            profile_tools[tool_profile].append(tool)
                        
                        # For each profile with tools, get the tools schema
                        for tool_profile, _ in profile_tools.items():
                            logger.debug(f"Getting tools for profile: {tool_profile}- {profile_tools[tool_profile]}")
                            try:
                                provider_tools = self.agent_services.agent_runner_service.get_agent_tools_schema(
                                    module_id=provider_id,
                                    profile=tool_profile  # Use the specific profile that provides tools
                                )
                                
                                # Filter tools to only include those in the provided list
                                provided_tool_names = [tool.name for tool in provided_tools]
                                filtered_tools = []
                                
                                for tool in provider_tools:
                                    logger.debug(f"Tool schema: {tool}")
                                    if "function" in tool and "name" in tool["function"]:
                                        tool_name = tool["function"]["name"]
                                        logger.debug(f"Checking tool: {tool_name}")
                                        if tool_name in provided_tool_names:
                                            logger.debug(f"Tool {tool_name} is provided by {provider_id}")
                                            # Prefix tool names with external_<module_id>_
                                            original_name = tool["function"]["name"]
                                            prefixed_name = f"external_{provider_id}_{original_name}"
                                            
                                            # Update name in the function schema
                                            tool["function"]["name"] = prefixed_name
                                            
                                            # Add provider info to description
                                            if "description" in tool["function"]:
                                                tool["function"]["description"] = f"[From module: {provider_id}] {tool['function']['description']}"
                                            
                                            # Add to our collection

                                            logger.debug(f"Adding tool: {tool['function']['name']}")
                                            filtered_tools.append(tool)
                                
                                all_tools.extend(filtered_tools)
                                
                            except Exception as e:
                                logger.error(f"Error getting tools from provider {provider_id} profile {tool_profile}: {e}", exc_info=True)
                        
                    except Exception as e:
                        logger.error(f"Error getting tools from provider {provider_id}: {e}", exc_info=True)
                        # Continue to next provider if one fails
                logger.debug(f"Total tools collected: {len(all_tools)}")
                logger.debug(f"All tools: {all_tools}")
                return all_tools
                
        except Exception as e:
            logger.error(f"Error getting provided tools schema: {e}", exc_info=True)
            return []  # Return empty list on error



    def exposed_execute_external_tool(
        self, 
        calling_module_id: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Execute a tool in another module based on the prefixed tool name.
        
        Args:
            calling_module_id: The module calling the external tool
            tool_name: The prefixed tool name (external_<module_id>_<tool_name>)
            parameters: The parameters to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        logger.debug(f"Module {calling_module_id} requested execution of external tool: {tool_name}")
        
        # Parse the tool name to extract module_id and actual tool name
        if not tool_name.startswith("external_"):
            raise ValueError(f"Invalid external tool name: {tool_name}. Must start with 'external_'")
        
        parts = tool_name.split("_", 2)  # Split into ["external", "module_id", "tool_name"]
        if len(parts) < 3:
            raise ValueError(f"Invalid external tool name format: {tool_name}. Expected format: external_<module_id>_<tool_name>")
        
        target_module_id = parts[1]
        actual_tool_name = parts[2]
        
        # Check if the calling module has permission to use tools from the target module
        with SessionLocal() as db:
            provide_check = db.execute(
                select(ModuleProvide).where(
                    ModuleProvide.provider_id == target_module_id,
                    ModuleProvide.receiver_id == calling_module_id,
                    ModuleProvide.resource_type == ProvideType.TOOL
                )
            ).first()
            
            if not provide_check:
                raise ValueError(f"Module {calling_module_id} does not have permission to use tools from {target_module_id}")
        
        # Get the kit config to find which profile has this tool
        try:
            kit_config = self.agent_services.module_service.get_module_kit_config(target_module_id)
            
            # Find which profile in the provider contains this tool
            tool_profile = None
            for tool in kit_config.provide.tools:
                if tool.name == actual_tool_name:
                    tool_profile = tool.profile
                    break
            
            if not tool_profile:
                logger.error(f"Tool {actual_tool_name} not found in module {target_module_id}'s provided tools")
                raise ValueError(f"Tool {actual_tool_name} is not available from module {target_module_id}")
                
            logger.info(f"Executing tool {actual_tool_name} from profile {tool_profile} in module {target_module_id}")
            
            # Execute the tool in the target module with the correct profile
            tool_result = self.agent_services.agent_runner_service.execute_agent_tool(
                module_id=target_module_id,
                profile=tool_profile,  # Use the specific profile that contains this tool
                tool_name=actual_tool_name,
                parameters=parameters
            )
            
            logger.info(f"Successfully executed external tool {tool_name} in module {target_module_id}")
            return tool_result
            
        except Exception as e:
            logger.error(f"Error executing external tool {tool_name} in module {target_module_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to execute external tool: {str(e)}")




    def exposed_get_supported_content_types(self) -> List[str]:
        """
        Returns the list of base MIME types that the platform's
        rendering layer currently supports displaying via <content> tags.
        """
        logger.debug("Request received for supported content types.")
        # Return the pre-calculated list loaded from config
        return SUPPORTED_CONTENT_TYPES_DEFINITION.get("supported_content_types", [])
    
    # --- Utility Methods ---
    def exposed_generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def exposed_generate_readable_uid(self) -> str:
        return generate_readable_uid()

    def exposed_ping(self) -> str:
        logger.debug("RPyC service received ping.")
        return "pong_rpyc"
    

