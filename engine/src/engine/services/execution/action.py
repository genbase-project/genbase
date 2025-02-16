import ast
import hashlib
import json
import os
import subprocess
import sys
import venv
import inspect
from pathlib import Path
from typing import Any, Dict, List, Set, Callable, Optional, Type, Union, get_args, get_origin, Literal
from types import UnionType

import cloudpickle
from pydantic import BaseModel, create_model

from engine.services.storage.repository import RepoService
from loguru import logger
import docker
import tempfile
from docker.errors import DockerException

class FunctionMetadata(BaseModel):
    """Function metadata in OpenAI function calling format"""
    name: str
    description: str
    parameters: Dict[str, Any]
    is_async: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format"""
        return {
            "name": self.name,
            "description": self.description, 
            "parameters": self.parameters,
            "is_async": self.is_async
        }

class FunctionParser(ast.NodeVisitor):
    """AST parser to extract function information in OpenAI schema format"""
    def __init__(self, function_name: str):
        self.function_name = function_name
        self.description = ""
        self.parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
        self.found = False
        self.is_async = False

    def _get_type_schema(self, annotation) -> Dict[str, Any]:
        """Convert Python type annotation to JSON schema"""
        if annotation is None:
            return {"type": "object"}

        if isinstance(annotation, ast.Name):
            type_map = {
                "str": {"type": "string"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "bool": {"type": "boolean"},
                "list": {"type": "array"},
                "Dict": {"type": "object"},  # Handle Dict as a name directly
                "dict": {"type": "object"},
                "Any": {"type": "object"}
            }
            return type_map.get(annotation.id, {"type": "object"})

        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == "Dict":
                    # For Dict type, we specify it's an object that can have additional properties
                    return {
                        "type": "object",
                        "additionalProperties": True
                    }
                elif annotation.value.id == "List":
                    return {
                        "type": "array",
                        "items": self._get_type_schema(annotation.slice)
                    }
                elif annotation.value.id == "Tuple":
                    # For tuples, represent as array with fixed items
                    if isinstance(annotation.slice, ast.Tuple):
                        return {
                            "type": "array",
                            "items": [self._get_type_schema(item) for item in annotation.slice.elts],
                            "minItems": len(annotation.slice.elts),
                            "maxItems": len(annotation.slice.elts)
                        }
                    else:
                        return {"type": "array"}
                elif annotation.value.id == "Optional":
                    type_schema = self._get_type_schema(annotation.slice)
                    if isinstance(type_schema["type"], list):
                        if "null" not in type_schema["type"]:
                            type_schema["type"].append("null")
                    else:
                        type_schema["type"] = [type_schema["type"], "null"]
                    return type_schema
                elif annotation.value.id == "Union":
                    if isinstance(annotation.slice, ast.Tuple):
                        types = []
                        for elt in annotation.slice.elts:
                            type_schema = self._get_type_schema(elt)
                            if "type" in type_schema:
                                if isinstance(type_schema["type"], list):
                                    types.extend(type_schema["type"])
                                else:
                                    types.append(type_schema["type"])
                        return {"type": list(set(types))} if types else {"type": "object"}
        
        # Default fallback
        return {"type": "object"}
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit a function definition"""
        if node.name == self.function_name:
            self.found = True
            
            # Get docstring
            docstring = ast.get_docstring(node)
            self.description = docstring or ""
            
            # Process parameters
            for arg in node.args.args:
                if arg.arg == 'self':  # Skip self parameter
                    continue
                    
                # Get type annotation if available
                annotation = arg.annotation
                param_schema = self._get_type_schema(annotation)
                
                # Add description from docstring
                if docstring:
                    param_docs = [
                        line.strip()
                        for line in docstring.split("\n")
                        if f":param {arg.arg}:" in line
                    ]
                    if param_docs:
                        param_desc = param_docs[0].split(":", 2)[-1].strip()
                        param_schema["description"] = param_desc

                self.parameters["properties"][arg.arg] = param_schema
                
                # If no default value, parameter is required
                defaults_offset = len(node.args.defaults)
                args_offset = len(node.args.args) - defaults_offset
                if node.args.args.index(arg) < args_offset:
                    self.parameters["required"].append(arg.arg)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit an async function definition"""
        self.is_async = True
        self.visit_FunctionDef(node)

class ActionError(Exception):
    """Base exception for action errors"""
    pass



class ActionService:
    """Service for executing Python functions with shared environment"""

    def __init__(self, repo_service: RepoService, venv_base_path: str = ".data/.venvs" , docker_image: str = "python:3.9-slim"):
        self.venv_base_path = Path(venv_base_path)
        self.venv_base_path.mkdir(exist_ok=True)
        self.installed_packages: Dict[str, Set[str]] = {}
        self.repo_service = repo_service

        self.docker_image = docker_image
        self.docker_client = docker.from_env()
        
        # Try to pull the image on initialization
        try:
            self.docker_client.images.pull(docker_image)
        except DockerException as e:
            logger.warning(f"Failed to pull Docker image: {e}")

    def _get_venv_path(self, folder_path: str) -> Path:
        """Get virtual environment path for a folder"""
        folder_hash = hashlib.md5(str(folder_path).encode()).hexdigest()[:8]
        return self.venv_base_path / f"venv_{folder_hash}"

    def _get_python_path(self, folder_path: str) -> Path:
        """Get Python executable path for a folder's virtual environment"""
        venv_path = self._get_venv_path(folder_path)
        return venv_path / ('Scripts' if os.name == 'nt' else 'bin') / ('python.exe' if os.name == 'nt' else 'python')

    def _get_pip_path(self, folder_path: str) -> Path:
        """Get pip executable path for a folder's virtual environment"""
        venv_path = self._get_venv_path(folder_path)
        return venv_path / ('Scripts' if os.name == 'nt' else 'bin') / ('pip.exe' if os.name == 'nt' else 'pip')

    def setup_environment(
        self,
        folder_path: str,
        requirements: List[str]
    ) -> Path:
        """Set up or update virtual environment for a folder"""
        try:
            folder_path = str(Path(folder_path).resolve())
            python_path = self._get_python_path(folder_path)

            # Create virtual environment if it doesn't exist
            if not python_path.exists():
                print(f"Creating new virtual environment for {folder_path}")
                venv.create(self._get_venv_path(folder_path), with_pip=True)
                self.installed_packages[folder_path] = set(['cloudpickle'])

                # Install cloudpickle by default
                subprocess.run(
                    [str(self._get_pip_path(folder_path)), 'install', 'cloudpickle'],
                    check=True,
                    capture_output=True,
                    text=True
                )

                # Add folder to Python path
                site_packages = self._get_venv_path(folder_path) / 'Lib' / 'site-packages' if os.name == 'nt' else self._get_venv_path(folder_path) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
                with open(site_packages / 'folder_path.pth', 'w') as f:
                    f.write(folder_path)

            # Install any missing requirements
            if folder_path not in self.installed_packages:
                self.installed_packages[folder_path] = set(['cloudpickle'])

            missing_packages = set(requirements) - self.installed_packages[folder_path]
            if missing_packages:
                print(f"Installing missing packages: {missing_packages}")
                try:
                    subprocess.run(
                        [str(self._get_pip_path(folder_path)), 'install'] + list(missing_packages),
                        check=True, 
                        capture_output=True,
                        text=True
                    )
                    logger.info(f"Installed missing packages: {missing_packages}")
                    self.installed_packages[folder_path].update(missing_packages)
                    logger.info(f"Installed missing packages: {missing_packages}")
                except subprocess.CalledProcessError as e:
                    raise ActionError(f"Failed to install requirements: {e.stderr}")

            return python_path

        except Exception as e:
            raise ActionError(f"Error setting up environment: {str(e)}")

    def get_function_metadata(
        self,
        folder_path: str,
        file_path: str,
        function_name: str
    ) -> FunctionMetadata:
        """Get function metadata in OpenAI function calling format"""
        logger.info(f"Getting metadata for function {function_name} in {file_path}")
        
        try:
            full_path = Path(folder_path) / file_path
            logger.debug(f"Full path: {full_path}")

            # Read the source code
            with open(full_path, 'r') as f:
                source = f.read()

            # Parse using AST
            tree = ast.parse(source)
            parser = FunctionParser(function_name)
            parser.visit(tree)

            if not parser.found:
                raise ActionError(f"Function {function_name} not found in {file_path}")

            return FunctionMetadata(
                name=function_name,
                description=parser.description,
                parameters=parser.parameters,
                is_async=parser.is_async
            )

        except Exception as e:
            logger.error(f"Error analyzing function: {str(e)}")
            raise ActionError(f"Error analyzing function: {str(e)}")



    def execute_function(
            self,
            folder_path: str,
            file_path: str,
            function_name: str,
            parameters: Dict[str, Any],
            requirements: List[str],
            env_vars: Dict[str, str],
            repo_name: str
        ) -> Any:
            """Execute a function in the shared environment"""
            try:
                # Convert to absolute paths
                venv_base = Path(self.venv_base_path).resolve()
                repo_path = Path(self.repo_service.get_repo_path(repo_name)).resolve()
                actions_path = Path(folder_path).resolve()
                
                # Setup/update virtual environment
                python_path = self.setup_environment(str(actions_path), requirements)

                logger.info(f"Executing function {function_name} in {file_path}")
                logger.info(f"Repository path: {repo_path}")
                logger.info(f"Actions folder path: {actions_path}")
                logger.info(f"Venv base path: {venv_base}")

                # Create venv directories if they don't exist
                venv_base.mkdir(parents=True, exist_ok=True)

                exec_script = f"""
import sys
import json
import cloudpickle
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Set environment variables
    env_vars = {env_vars}
    for key, value in env_vars.items():
        os.environ[key] = str(value)

    # Convert paths to Path objects
    repo_path = Path(r'{repo_path}')
    action_path = Path(r'{actions_path}')
    
    logger.info(f"Repository path: {{repo_path}}")
    logger.info(f"Action path: {{action_path}}")
    
    # Add paths to sys.path
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    if str(action_path) not in sys.path:
        sys.path.insert(0, str(action_path))
    
    # Set current working directory to repo path
    os.chdir(repo_path)
    
    # Get absolute path to the module file
    module_file = action_path / r'{file_path}'
    logger.info(f"Loading module from: {{module_file}}")
    
    if not module_file.exists():
        raise FileNotFoundError(f"Module file not found: {{module_file}}")
    
    # Import the module
    import importlib.util
    spec = importlib.util.spec_from_file_location('dynamic_module', str(module_file))
    if spec is None:
        raise ImportError(f"Could not find module: {{module_file}}")
        
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Could not load module: {{module_file}}")
        
    spec.loader.exec_module(module)
    
    # Get and execute the function
    if not hasattr(module, '{function_name}'):
        raise AttributeError(f"Function {{function_name}} not found in {{module_file}}")
        
    func = getattr(module, '{function_name}')
    
    # Load parameters from absolute path
    params_file = Path(r'{venv_base}/params.json')
    with open(params_file, 'r') as f:
        parameters = json.load(f)
    
    # Execute
    result = func(**parameters)
    
    # Save result to absolute path
    result_file = Path(r'{venv_base}/result.json')
    with open(result_file, 'wb') as f:
        cloudpickle.dump(result, f)
        
except Exception as e:
    import traceback
    error_file = Path(r'{venv_base}/error.txt')
    error_file.write_text(traceback.format_exc())
    raise
"""
                # Use absolute paths for all files
                exec_path = (venv_base / "exec.py").resolve()
                params_path = (venv_base / "params.json").resolve()
                result_path = (venv_base / "result.json").resolve()
                error_path = (venv_base / "error.txt").resolve()

                try:
                    # Write execution script
                    logger.info(f"Writing execution script to {exec_path}")
                    exec_path.write_text(exec_script)
                    
                    # Save parameters
                    logger.info(f"Writing parameters to {params_path}")
                    with open(params_path, 'w') as f:
                        json.dump(parameters, f)
                    

                    process_env = {}
                    process_env.update({key: str(value) for key, value in env_vars.items()})

                    # Execute
                    try:
                        process = subprocess.run(
                            [str(python_path), str(exec_path)],
                            check=True,
                            capture_output=True,
                            text=True,
                            env=process_env
                        )
                    except subprocess.CalledProcessError as e:
                        error_msg = f"Process failed with exit code {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
                        raise ActionError(f"Error executing function: {error_msg}")

                    if process.returncode != 0:
                        logger.info(process.stdout)
                        logger.info(process.stderr)

                    # Check for errors
                    if error_path.exists():
                        error_msg = error_path.read_text()
                        raise ActionError(f"Function execution failed: {error_msg}")

                    # Load result
                    with open(result_path, "rb") as f:
                        result = cloudpickle.load(f)

                    return result

                finally:
                    # Cleanup
                    for path in [exec_path, params_path, result_path, error_path]:
                        try:
                            if path.exists():
                                path.unlink()
                        except:
                            pass

            except Exception as e:
                raise ActionError(f"Error executing function: {str(e)}")

# # Example test code demonstrating function metadata parsing capabilities
# if __name__ == "__main__":
#     from enum import Enum
#     from typing import List, Optional, Union, Literal
#     from pydantic import BaseModel, Field
    
#     # Example enum and Pydantic models
#     class UserRole(str, Enum):
#         ADMIN = "admin"
#         USER = "user"
#         GUEST = "guest"
    
#     class UserProfile(BaseModel):
#         """User profile information"""
#         name: str = Field(..., description="User's full name")
#         age: Optional[int] = Field(None, description="User's age")
#         roles: List[UserRole] = Field(default_factory=list, description="User's roles")
    
#     class TeamSettings(BaseModel):
#         """Team configuration settings"""
#         team_name: str = Field(..., description="Name of the team")
#         max_members: int = Field(default=10, description="Maximum number of team members")
#         features: List[str] = Field(default_factory=list, description="Enabled features")
    
#     # Example function with various type hints
#     async def create_team(
#         profile: UserProfile,
#         team_config: TeamSettings,
#         team_type: Literal["public", "private", "internal"],
#         metadata: Optional[Dict[str, Any]] = None,
#         sync_data: Union[bool, List[str]] = False
#     ) -> Dict[str, Any]:
#         """Create a new team with the given configuration.
        
#         Args:
#             profile: User profile creating the team
#             team_config: Team configuration settings
#             team_type: Type of team to create
#             metadata: Optional metadata for the team
#             sync_data: Whether to sync data or list of data types to sync
            
#         Returns:
#             Dictionary with team creation result
#         """
#         pass  # Function implementation not needed for schema generation example
    
#     # Example usage
#     try:
#         logger.info("Generating schema for example function...")
#         schema = function_to_schema(create_team)
#         logger.info("Generated schema:")
#         logger.info(json.dumps(schema, indent=2))
        
#         # The schema will include:
#         # - Complex types from Pydantic models (UserProfile, TeamSettings)
#         # - Literal types with specific allowed values
#         # - Optional parameters with defaults
#         # - Union types
#         # - Async function detection
#         # - Parameter descriptions from docstrings
        
#     except Exception as e:
#         logger.error(f"Error in example: {str(e)}")
