# engine/services/operation.py

from dataclasses import dataclass
import inspect
import typing
from typing import Dict, Any, Optional
import cloudpickle
import importlib.util
import textwrap

@dataclass
class FunctionMetadata:
    """Function metadata"""
    docstring: str
    parameters: Dict[str, Any]
    return_type: Any
    is_async: bool

class OperationError(Exception):
    """Base exception for operation errors"""
    pass

class OperationService:
    """Service for executing Python functions"""
    
    def get_function_metadata(self, file_path: str, function_name: str) -> FunctionMetadata:
        """
        Extract metadata about a function from a Python file.
        
        Args:
            file_path: Path to the Python file
            function_name: Name of the function to analyze
        
        Returns:
            FunctionMetadata object containing function information
        """
        try:
            spec = importlib.util.spec_from_file_location("dynamic_module", file_path)
            if not spec or not spec.loader:
                raise OperationError(f"Could not load module from {file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, function_name):
                raise OperationError(f"Function {function_name} not found in {file_path}")
                
            func = getattr(module, function_name)
            
            # Extract metadata
            signature = inspect.signature(func)
            type_hints = typing.get_type_hints(func)
            docstring = inspect.getdoc(func) or ""
            is_async = inspect.iscoroutinefunction(func)
            
            # Process parameters
            parameters = {}
            for param_name, param in signature.parameters.items():
                param_type = type_hints.get(param_name, Any)
                parameters[param_name] = {
                    'type': param_type,
                    'default': None if param.default == inspect.Parameter.empty else param.default,
                    'kind': str(param.kind)
                }
            
            return_type = type_hints.get('return', Any)
            
            return FunctionMetadata(
                docstring=docstring,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async
            )
            
        except Exception as e:
            raise OperationError(f"Error analyzing function: {str(e)}")

    def execute_function(
        self, 
        file_path: str, 
        function_name: str, 
        parameters: Dict[str, Any],
        sandbox: bool = True
    ) -> Any:
        """
        Execute a function with given parameters.
        
        Args:
            file_path: Path to the Python file
            function_name: Name of the function to execute
            parameters: Dictionary of parameter names and values
            sandbox: Whether to use RestrictedPython sandbox
        
        Returns:
            Result of the function execution
        """
        try:
            # First get the metadata to validate parameters
            metadata = self.get_function_metadata(file_path, function_name)
            
            # Validate parameters
            for param_name, param_info in metadata.parameters.items():
                if param_name not in parameters and param_info['default'] is None:
                    raise OperationError(f"Required parameter {param_name} not provided")
            
            # For now, we'll use unrestricted execution since it's just basic Python functions
            # In a production environment, you'd want to implement proper sandboxing
            return self._execute_unrestricted(file_path, function_name, parameters)
            
        except Exception as e:
            raise OperationError(f"Error executing function: {str(e)}")
    
    def _execute_unrestricted(
        self, 
        file_path: str, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute function using cloudpickle"""
        try:
            spec = importlib.util.spec_from_file_location("dynamic_module", file_path)
            if not spec or not spec.loader:
                raise OperationError(f"Could not load module from {file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, function_name):
                raise OperationError(f"Function {function_name} not found in {file_path}")
                
            func = getattr(module, function_name)
            
            # Serialize and deserialize to ensure clean execution context
            func = cloudpickle.loads(cloudpickle.dumps(func))
            
            return func(**parameters)
        except Exception as e:
            raise OperationError(f"Error executing function: {str(e)}")