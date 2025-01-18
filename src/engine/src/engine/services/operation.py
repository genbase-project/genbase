# engine/services/operation.py

from dataclasses import dataclass
import inspect
import typing
from typing import Dict, Any, Optional, List
import cloudpickle
import importlib.util
import venv
import subprocess
import os
from pathlib import Path
import json
import sys
import hashlib

@dataclass
class FunctionMetadata:
    """Function metadata"""
    docstring: str
    parameters: Dict[str, Any]
    return_type: Any
    is_async: bool
    required_packages: List[str]

class OperationError(Exception):
    """Base exception for operation errors"""
    pass

class OperationService:
    """Service for executing Python functions with isolated environments"""
    
    def __init__(self, venv_base_path: str = ".venvs"):
        """Initialize service with venv path"""
        self.venv_base_path = Path(venv_base_path)
        self.venv_base_path.mkdir(exist_ok=True)
        self._venv_cache = {}  # Cache for virtual environments
    
    def _get_env_hash(self, requirements: List[str]) -> str:
        """Generate a unique hash for a set of requirements"""
        # Always include cloudpickle in requirements
        all_requirements = set(requirements + ['cloudpickle'])
        sorted_reqs = sorted(all_requirements)
        req_str = ','.join(sorted_reqs)
        return hashlib.md5(req_str.encode()).hexdigest()[:8]
    
    def _create_or_get_venv(self, requirements: List[str]) -> Path:
        """Create virtual environment if it doesn't exist or return existing one"""
        # Ensure cloudpickle is in requirements
        requirements = list(set(requirements + ['cloudpickle']))
        
        env_hash = self._get_env_hash(requirements)
        venv_path = self.venv_base_path / f"venv_{env_hash}"
        python_path = venv_path / ('Scripts' if os.name == 'nt' else 'bin') / ('python.exe' if os.name == 'nt' else 'python')
        
        if not python_path.exists():
            print(f"Creating new virtual environment with requirements: {requirements}")
            # Create virtual environment
            venv.create(venv_path, with_pip=True)
            
            # Get pip path
            pip_path = venv_path / ('Scripts' if os.name == 'nt' else 'bin') / ('pip.exe' if os.name == 'nt' else 'pip')
            
            try:
                # Install cloudpickle first
                subprocess.run(
                    [str(pip_path), 'install', 'cloudpickle'],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                # Install other requirements
                if requirements:
                    subprocess.run(
                        [str(pip_path), 'install'] + requirements,
                        check=True,
                        capture_output=True,
                        text=True
                    )
            except subprocess.CalledProcessError as e:
                raise OperationError(f"Failed to install requirements: {e.stderr}")
        
        return python_path

    def _execute_in_venv(
        self, 
        python_path: Path, 
        file_path: str, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute function in virtual environment"""
        # Convert to raw string path
        file_path = str(Path(file_path).resolve()).replace('\\', '/')
        
        # Create a temporary file with execution code
        exec_code = f"""
import sys
import json
import cloudpickle
import importlib.util

try:
    # Load the function
    spec = importlib.util.spec_from_file_location('module', r'{file_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, '{function_name}')

    # Load parameters
    with open(r'{self.venv_base_path}/params.json', 'r') as f:
        parameters = json.load(f)

    # Execute function
    result = func(**parameters)

    # Save result
    with open(r'{self.venv_base_path}/result.json', 'wb') as f:
        cloudpickle.dump(result, f)
except Exception as e:
    import traceback
    with open(r'{self.venv_base_path}/error.txt', 'w') as f:
        f.write(traceback.format_exc())
    raise
"""
        exec_path = (self.venv_base_path / "exec.py").resolve()
        params_path = (self.venv_base_path / "params.json").resolve()
        result_path = (self.venv_base_path / "result.json").resolve()
        error_path = (self.venv_base_path / "error.txt").resolve()

        try:
            # Write execution code
            with open(exec_path, "w") as f:
                f.write(exec_code)
            
            # Save parameters
            with open(params_path, "w") as f:
                json.dump(parameters, f)
            
            # Execute in virtual environment
            process = subprocess.run(
                [str(python_path), str(exec_path)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Check for error file
            if error_path.exists():
                with open(error_path, 'r') as f:
                    error_msg = f.read()
                raise OperationError(f"Function execution failed: {error_msg}")
            
            # Load result
            with open(result_path, "rb") as f:
                result = cloudpickle.load(f)
            
            return result
            
        except subprocess.CalledProcessError as e:
            if error_path.exists():
                with open(error_path, 'r') as f:
                    error_msg = f.read()
                raise OperationError(f"Function execution failed: {error_msg}")
            raise OperationError(f"Function execution failed: {e.stderr}")
        finally:
            # Cleanup temporary files
            for path in [exec_path, params_path, result_path, error_path]:
                try:
                    if path.exists():
                        path.unlink()
                except:
                    pass

    def extract_requirements(self, file_path: str) -> List[str]:
        """Extract import statements from file"""
        standard_libs = {
            'os', 'sys', 'json', 'typing', 'dataclasses', 'collections', 
            'datetime', 'time', 'math', 'random', 'itertools', 'functools',
            'inspect', 'ast'
        }
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            imports = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract package name (first part of import)
                    parts = line.split()
                    if line.startswith('from '):
                        package = parts[1].split('.')[0]
                    else:
                        package = parts[1].split('.')[0]
                    
                    if package not in standard_libs:
                        imports.append(package)
            
            return list(set(imports))
            
        except Exception as e:
            raise OperationError(f"Failed to extract requirements: {str(e)}")

    def execute_function(
        self, 
        file_path: str, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute function in isolated environment"""
        try:
            # Extract requirements from file
            requirements = self.extract_requirements(file_path)
            
            # Create or get virtual environment
            python_path = self._create_or_get_venv(requirements)
            
            # Execute function
            result = self._execute_in_venv(
                python_path,
                file_path,
                function_name,
                parameters
            )
            
            return result
            
        except Exception as e:
            raise OperationError(f"Error executing function: {str(e)}")

    def get_function_metadata(self, file_path: str, function_name: str) -> FunctionMetadata:
        """Get function metadata"""
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
            
            # Extract requirements
            required_packages = self.extract_requirements(file_path)
            
            return FunctionMetadata(
                docstring=docstring,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async,
                required_packages=required_packages
            )
            
        except Exception as e:
            raise OperationError(f"Error analyzing function: {str(e)}")