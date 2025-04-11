import inspect
import re
from typing import Any, Callable, Dict, List, Literal, Optional, Union, get_type_hints
from engine.services.execution.tool import FunctionMetadata
from loguru import logger

class InternalToolManager:
    """
    Manages registration and metadata extraction for custom tools.
    Handles JSON schema generation for function definitions.
    """
    
    def __init__(self):
        """Initialize the custom action manager"""
        # Dictionary to store custom (internal) actions
        self._internal_tools: Dict[str, Callable] = {}
        # Metadata cache for custom actions
        self._internal_tool_metadata: Dict[str, FunctionMetadata] = {}
        logger.info("InternalToolManager initialized")
    
    def register_action(self, name: str, func: Callable, description: str = None) -> None:
        """
        Register a method as a custom action that can be called by the LLM.
        
        Args:
            name: Name of the action (must be unique)
            func: Method reference to call when action is invoked
            description: Optional description of what the action does
        """
        logger.info(f"Registering action '{name}' with function {func}")
        
        if name in self._internal_tools:
            logger.warning(f"Custom action '{name}' already registered")
            raise ValueError(f"Custom action '{name}' already registered")
            
        self._internal_tools[name] = func
        
        # Extract metadata and cache it
        try:
            metadata = self._extract_function_metadata(func, name, description)
            self._internal_tool_metadata[name] = metadata
            logger.info(f"Successfully registered action '{name}' with metadata: {metadata}")
        except Exception as e:
            logger.error(f"Failed to extract metadata for action '{name}': {str(e)}")
            # Remove action from registry if metadata extraction fails
            del self._internal_tools[name]
            raise
    
    def clear_tools(self) -> None:
        """Clear all registered custom actions"""
        logger.info("Clearing all registered actions")
        self._internal_tools = {}
        self._internal_tool_metadata = {}
    
    def register_tools(self, functions: Dict[str, Callable]) -> None:
        """
        Register multiple custom actions at once.
        
        Args:
            functions: Dictionary mapping action names to function references
        """
        logger.info(f"Registering multiple actions: {list(functions.keys())}")
        self.clear_tools()
        
        for name, func in functions.items():
            try:
                # Extract description from docstring if available
                description = inspect.getdoc(func)
                logger.debug(f"Function '{name}' docstring: {description}")
                if not description:
                    description = f"Execute the {name} action"
                    logger.debug(f"No docstring found for '{name}', using default description")
                
                self.register_action(name, func, description)
            except Exception as e:
                logger.error(f"Failed to register action '{name}': {str(e)}")
    
    def get_tool_metadata(self, action_name: str) -> Optional[FunctionMetadata]:
        """
        Get metadata for a custom action by name
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            FunctionMetadata or None if action not found
        """
        metadata = self._internal_tool_metadata.get(action_name)
        logger.debug(f"Retrieved metadata for action '{action_name}': {metadata}")
        return metadata
    
    def get_tool_function(self, action_name: str) -> Optional[Callable]:
        """
        Get the function reference for a custom action
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            Function reference or None if not found
        """
        function = self._internal_tools.get(action_name)
        logger.debug(f"Retrieved function for action '{action_name}': {function}")
        return function
    
    def get_all_tools(self) -> List[str]:
        """
        Get names of all registered custom actions
        
        Returns:
            List of tool names
        """
        actions = list(self._internal_tools.keys())
        logger.debug(f"All registered tools: {actions}")
        return actions
    
    def has_tool(self, action_name: str) -> bool:
        """
        Check if a custom action exists
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            True if action exists, False otherwise
        """
        exists = action_name in self._internal_tools
        logger.debug(f"Action '{action_name}' exists: {exists}")
        return exists
        
    def get_tool_definitions(self, tool_names: Optional[Union[List[str], Literal["all", "none"]]] = None) -> List[Dict[str, Any]]:
        """
        Get tool definitions for specified tools in OpenAI format
        
        Args:
            _nametools: Optional list of tool names to include, 
                        "all" for all tools, "none" for no tools,
                        or None for all registered tool
            
        Returns:
            List of tool definitions
        """
        logger.info(f"Getting tool definitions for tools: {tool_names}")
        logger.info(f"Currently registered tools: {self.get_all_tools()}")
        logger.info(f"Tool metadata available: {list(self._internal_tool_metadata.keys())}")
        
        # Handle special string values
        if tool_names == "all" or tool_names is None:
            tool_names = self.get_all_tools()
            logger.debug(f"Using all registered actions: {tool_names}")
        elif tool_names == "none":
            logger.debug("No actions requested")
            return []
        else:
            # If it's a list, filter to only include actions that exist
            original_names = tool_names
            tool_names = [name for name in tool_names if self.has_tool(name)]
            logger.debug(f"Filtered action names from {original_names} to {tool_names}")
        
        tools = []
        for action_name in tool_names:
            metadata = self._internal_tool_metadata.get(action_name)
            logger.debug(f"Metadata for action '{action_name}': {metadata}")
            
            if metadata:
                tool = {
                    "type": "function",
                    "function": {
                        "name": action_name,
                        "description": metadata.description,
                        "parameters": metadata.parameters
                    }
                }
                tools.append(tool)
                logger.debug(f"Added tool definition for '{action_name}'")
            else:
                logger.warning(f"No metadata found for action '{action_name}', skipping")
        
        logger.info(f"Generated {len(tools)} tool definitions")
        return tools

    async def execute_tool(self, action_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a custom action by name
        
        Args:
            action_name: Name of the action to execute
            parameters: Parameters to pass to the action
            
        Returns:
            Result of the action
            
        Raises:
            ValueError: If action not found
        """
        logger.info(f"Executing action '{action_name}' with parameters: {parameters}")
        
        if not self.has_tool(action_name):
            logger.error(f"Custom action '{action_name}' not found")
            raise ValueError(f"Custom action '{action_name}' not found")
        
        func = self._internal_tools[action_name]
        try:
            if inspect.iscoroutinefunction(func):
                # Handle async functions
                logger.debug(f"Executing async function '{action_name}'")
                return await func(**parameters)
            else:
                # Handle synchronous functions
                logger.debug(f"Executing sync function '{action_name}'")
                return func(**parameters)
        except Exception as e:
            logger.error(f"Error executing action '{action_name}': {str(e)}")
            raise
    
    def _extract_function_metadata(self, func: Callable, name: str, description: str = None) -> FunctionMetadata:
        """
        Extract OpenAI function metadata from a method
        
        Args:
            func: Method to extract metadata from
            name: Name to use for the function
            description: Optional description override
            
        Returns:
            FunctionMetadata: Metadata in OpenAI function format
        """
        logger.debug(f"Extracting metadata for function '{name}'")
        
        # Get docstring for description if not provided
        if description is None:
            docstring = inspect.getdoc(func)
            logger.debug(f"Original docstring: {docstring}")
            
            if docstring:
                # Use first paragraph of docstring as description
                description = docstring.split('\n\n')[0].strip()
                logger.debug(f"Using first paragraph as description: {description}")
            else:
                description = f"Execute the {name} action"
                logger.debug(f"No docstring found, using default description")
            
        # Get function signature
        try:
            sig = inspect.signature(func)
            logger.debug(f"Function signature: {sig}")
        except ValueError as e:
            logger.error(f"Could not get signature for function '{name}': {str(e)}")
            sig = inspect.Signature()  # Empty signature
        
        # Get type hints if available
        try:
            type_hints = get_type_hints(func)
            logger.debug(f"Type hints: {type_hints}")
        except Exception as e:
            logger.warning(f"Could not get type hints for function '{name}': {str(e)}")
            type_hints = {}
        
        # Build parameters schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                logger.debug(f"Skipping 'self' parameter")
                continue
                
            # Get parameter type
            param_type = type_hints.get(param_name, Any)
            logger.debug(f"Parameter '{param_name}' has type: {param_type}")
            
            # Convert type to JSON schema type
            try:
                json_type = self._type_to_json_schema(param_type)
                logger.debug(f"Converted type to JSON schema: {json_type}")
            except Exception as e:
                logger.warning(f"Error converting type to JSON schema for '{param_name}': {str(e)}")
                json_type = {"type": "object"}
            
            # Extract parameter description from docstring
            param_description = self._extract_param_description(func, param_name)
            logger.debug(f"Parameter description: {param_description}")
            
            # Create parameter property
            param_property = {}
            
            # Handle complex schema types (oneOf, enum, etc.)
            if "type" in json_type:
                param_property["type"] = json_type["type"]
            
            if "oneOf" in json_type:
                param_property["oneOf"] = json_type["oneOf"]
            
            if "enum" in json_type:
                param_property["enum"] = json_type["enum"]
            
            # Add description
            param_property["description"] = param_description or f"Parameter {param_name}"
            
            # If array or object, add items/properties
            if "items" in json_type:
                param_property["items"] = json_type["items"]
                
            if "properties" in json_type:
                param_property["properties"] = json_type["properties"]
                if "required" in json_type:
                    param_property["required"] = json_type["required"]
            
            # Add to properties dictionary
            parameters["properties"][param_name] = param_property
            logger.debug(f"Added parameter property: {param_property}")
                
            # Add to required list if no default value
            if param.default is param.empty:
                parameters["required"].append(param_name)
                logger.debug(f"Parameter '{param_name}' is required")
        
        metadata = FunctionMetadata(
            name=name,
            description=description,
            parameters=parameters,
            is_async=inspect.iscoroutinefunction(func)
        )
        
        logger.debug(f"Created metadata: {metadata}")
        return metadata
        
    def _extract_param_description(self, func: Callable, param_name: str) -> Optional[str]:
        """
        Extract parameter description from function docstring
        
        Args:
            func: Function to extract from
            param_name: Parameter name to find
            
        Returns:
            Description string or None if not found
        """
        docstring = inspect.getdoc(func)
        if not docstring:
            logger.debug(f"No docstring found for parameter '{param_name}'")
            return None
        
        logger.debug(f"Looking for parameter '{param_name}' in docstring")
            
        # Try to find parameter in Args section using common docstring formats
        
        # Google style
        pattern = rf"(?:Args|Arguments):\s+.*?{param_name}\s*:\s*(.*?)(?:\n\s*\w+\s*:|$)"
        match = re.search(pattern, docstring, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            logger.debug(f"Found Google-style description: {desc}")
            return desc
            
        # Numpy/Sphinx style
        pattern = rf"Parameters\s+.*?{param_name}\s*:\s*(.*?)(?:\n\s*\w+\s*:|$)"
        match = re.search(pattern, docstring, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            logger.debug(f"Found Numpy/Sphinx-style description: {desc}")
            return desc
        
        logger.debug(f"No description found for parameter '{param_name}'")
        return None
        
    def _type_to_json_schema(self, type_hint: Any) -> Dict[str, Any]:
        """
        Convert Python type hint to JSON schema type
        
        Args:
            type_hint: Python type hint
            
        Returns:
            Dict with JSON schema type information
        """
        logger.debug(f"Converting type hint to JSON schema: {type_hint}")
        
        # Handle common types
        if type_hint is str:
            return {"type": "string"}
        elif type_hint is int:
            return {"type": "integer"}
        elif type_hint is float:
            return {"type": "number"}
        elif type_hint is bool:
            return {"type": "boolean"}
        elif type_hint is None or type_hint is type(None):
            return {"type": "null"}
        elif hasattr(type_hint, "__origin__"):
            # Handle generics like List, Dict, etc.
            origin = type_hint.__origin__
            args = type_hint.__args__
            logger.debug(f"Generic type with origin {origin} and args {args}")
            
            if origin is list or origin is List:
                item_type = self._type_to_json_schema(args[0])
                return {
                    "type": "array",
                    "items": item_type
                }
            elif origin is dict or origin is Dict:
                # For simplicity, assume dict keys are strings
                value_type = self._type_to_json_schema(args[1])
                return {
                    "type": "object",
                    "additionalProperties": value_type
                }
            elif origin is Union or origin is Optional:
                # Handle Optional/Union
                if type(None) in args:
                    # This is Optional[X]
                    non_none_args = [arg for arg in args if arg is not type(None)]
                    if len(non_none_args) == 1:
                        result = self._type_to_json_schema(non_none_args[0])
                        return result
                # For regular unions, return a oneOf schema
                types = [self._type_to_json_schema(arg) for arg in args if arg is not type(None)]
                if len(types) > 1:
                    return {"oneOf": types}
                elif len(types) == 1:
                    return types[0]
                return {"type": "object"}
            elif origin is Literal:
                # Handle Literal type (enum)
                return {
                    "type": "string",
                    "enum": list(args)
                }
        elif hasattr(type_hint, "__name__") and type_hint.__name__ == "Enum":
            # Handle Enum classes
            try:
                return {
                    "type": "string",
                    "enum": [e.name for e in type_hint]
                }
            except:
                return {"type": "string"}
                
        # Try to handle Pydantic models if available
        try:
            if hasattr(type_hint, "model_json_schema"):
                schema = type_hint.model_json_schema()
                logger.debug(f"Got schema from Pydantic model: {schema}")
                return schema
        except Exception as e:
            logger.warning(f"Error getting Pydantic schema: {str(e)}")
            
        # Default for unknown/complex types
        logger.debug(f"Using default object schema for type: {type_hint}")
        return {"type": "object"}