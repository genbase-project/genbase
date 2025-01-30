import ast
import hashlib
import json
import os
import subprocess
import sys
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

import cloudpickle

from engine.services.storage.repository import RepoService
from engine.utils.logging import logger


@dataclass
class FunctionMetadata:
    """Function metadata in OpenAI function calling format"""
    name: str
    description: str
    parameters: Dict[str, Any]
    is_async: bool

class ActionError(Exception):
    """Base exception for action errors"""
    pass

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

    def visit_FunctionDef(self, node):
        if node.name == self.function_name:
            self.found = True

            # Get docstring
            if ast.get_docstring(node):
                self.description = ast.get_docstring(node)

            # Get parameters
            for arg in node.args.args:
                param_schema = self._get_type_schema(arg.annotation)
                
                # Add description if available in docstring
                if self.description:
                    param_docs = [
                        line.strip()
                        for line in self.description.split("\n")
                        if f":param {arg.arg}:" in line
                    ]
                    if param_docs:
                        param_desc = param_docs[0].split(":", 2)[-1].strip()
                        param_schema["description"] = param_desc

                self.parameters["properties"][arg.arg] = param_schema

                # Add to required list if no default value
                default_offset = len(node.args.args) - len(node.args.defaults)
                if node.args.args.index(arg) < default_offset:
                    self.parameters["required"].append(arg.arg)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition"""
        self.is_async = True
        self.visit_FunctionDef(node)



class ActionService:
    """Service for executing Python functions with shared environment"""

    def __init__(self, repo_service: RepoService, venv_base_path: str = ".data/.venvs"  ):
        self.venv_base_path = Path(venv_base_path)
        self.venv_base_path.mkdir(exist_ok=True)
        self.installed_packages: Dict[str, Set[str]] = {}
        self.repo_service = repo_service

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
        try:
            full_path = Path(folder_path) / file_path

            with open(full_path, 'r') as f:
                source = f.read()

            # Parse the source code
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
                repo_path = Path(self.repo_service._get_repo_path(repo_name)).resolve()
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

                    # Execute
                    try:
                        process = subprocess.run(
                            [str(python_path), str(exec_path)],
                            check=True,
                            capture_output=True,
                            text=True
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