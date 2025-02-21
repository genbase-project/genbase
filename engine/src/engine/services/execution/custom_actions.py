import inspect
import re
from typing import Any, Callable, Dict, List, Literal, Optional, Union, get_type_hints
from engine.services.execution.action import FunctionMetadata
from loguru import logger

class CustomActionManager:
    """
    Manages registration and metadata extraction for custom actions.
    Handles JSON schema generation for function definitions.
    """
    
    def __init__(self):
        """Initialize the custom action manager"""
        # Dictionary to store custom (internal) actions
        self._custom_actions: Dict[str, Callable] = {}
        # Metadata cache for custom actions
        self._custom_action_metadata: Dict[str, FunctionMetadata] = {}
    
    def register_action(self, name: str, func: Callable, description: str = None) -> None:
        """
        Register a method as a custom action that can be called by the LLM.
        
        Args:
            name: Name of the action (must be unique)
            func: Method reference to call when action is invoked
            description: Optional description of what the action does
        """
        if name in self._custom_actions:
            raise ValueError(f"Custom action '{name}' already registered")
            
        self._custom_actions[name] = func
        
        # Extract metadata and cache it
        metadata = self._extract_function_metadata(func, name, description)
        self._custom_action_metadata[name] = metadata
    
    def clear_actions(self) -> None:
        """Clear all registered custom actions"""
        self._custom_actions = {}
        self._custom_action_metadata = {}
    
    def register_actions(self, functions: Dict[str, Callable]) -> None:
        """
        Register multiple custom actions at once.
        
        Args:
            functions: Dictionary mapping action names to function references
        """
        self.clear_actions()
        for name, func in functions.items():
            # Extract description from docstring if available
            description = inspect.getdoc(func) or f"Execute the {name} action"
            self.register_action(name, func, description)
    
    def get_action_metadata(self, action_name: str) -> Optional[FunctionMetadata]:
        """
        Get metadata for a custom action by name
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            FunctionMetadata or None if action not found
        """
        return self._custom_action_metadata.get(action_name)
    
    def get_action_function(self, action_name: str) -> Optional[Callable]:
        """
        Get the function reference for a custom action
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            Function reference or None if not found
        """
        return self._custom_actions.get(action_name)
    
    def get_all_actions(self) -> List[str]:
        """
        Get names of all registered custom actions
        
        Returns:
            List of action names
        """
        return list(self._custom_actions.keys())
    
    def has_action(self, action_name: str) -> bool:
        """
        Check if a custom action exists
        
        Args:
            action_name: Name of the custom action
            
        Returns:
            True if action exists, False otherwise
        """
        return action_name in self._custom_actions
    
    def get_tool_definitions(self, action_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get tool definitions for specified actions in OpenAI format
        
        Args:
            action_names: Optional list of action names to include, 
                          or None for all registered actions
            
        Returns:
            List of tool definitions
        """
        if action_names is None:
            action_names = self.get_all_actions()
        else:
            # Filter to only include actions that exist
            action_names = [name for name in action_names if self.has_action(name)]
        
        tools = []
        for action_name in action_names:
            metadata = self._custom_action_metadata.get(action_name)
            if metadata:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": action_name,
                        "description": metadata.description,
                        "parameters": metadata.parameters
                    }
                })
        
        return tools
    
    async def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> Any:
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
        if not self.has_action(action_name):
            raise ValueError(f"Custom action '{action_name}' not found")
        
        func = self._custom_actions[action_name]
        if inspect.iscoroutinefunction(func):
            # Handle async functions
            return await func(**parameters)
        else:
            # Handle synchronous functions
            return func(**parameters)
    
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
        # Get docstring for description if not provided
        if description is None:
            docstring = inspect.getdoc(func)
            if docstring:
                # Use first paragraph of docstring as description
                description = docstring.split('\n\n')[0].strip()
            else:
                description = f"Execute the {name} action"
            
        # Get function signature
        sig = inspect.signature(func)
        
        # Get type hints if available
        type_hints = get_type_hints(func)
        
        # Build parameters schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue
                
            # Get parameter type
            param_type = type_hints.get(param_name, Any)
            
            # Convert type to JSON schema type
            json_type = self._type_to_json_schema(param_type)
            
            # Extract parameter description from docstring
            param_description = self._extract_param_description(func, param_name)
            
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
                
            # Add to required list if no default value
            if param.default is param.empty:
                parameters["required"].append(param_name)
        
        return FunctionMetadata(
            name=name,
            description=description,
            parameters=parameters,
            is_async=inspect.iscoroutinefunction(func)
        )
        
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
            return None
            
        # Try to find parameter in Args section using common docstring formats
        
        # Google style
        pattern = rf"(?:Args|Arguments):\s+.*?{param_name}\s*:\s*(.*?)(?:\n\s*\w+\s*:|$)"
        match = re.search(pattern, docstring, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        # Numpy/Sphinx style
        pattern = rf"Parameters\s+.*?{param_name}\s*:\s*(.*?)(?:\n\s*\w+\s*:|$)"
        match = re.search(pattern, docstring, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
        
    def _type_to_json_schema(self, type_hint: Any) -> Dict[str, Any]:
        """
        Convert Python type hint to JSON schema type
        
        Args:
            type_hint: Python type hint
            
        Returns:
            Dict with JSON schema type information
        """
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
                return type_hint.model_json_schema()
        except:
            pass
            
        # Default for unknown/complex types
        return {"type": "object"}