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
    def __init__(self, repo_service: RepoService):
        self.repo_service = repo_service
        self.docker_client = docker.from_env()
        self.cached_images = {}  # Cache for storing prepared images

    def _get_cache_tag(self, base_image: str, requirements: List[str]) -> str:
        """Generate a unique tag for caching based on base image and requirements"""
        # Create a unique identifier based on base image and requirements
        requirements_str = ','.join(sorted(requirements))
        cache_key = hashlib.md5(requirements_str.encode()).hexdigest()[:12]
        
        # Remove any invalid characters from base image name
        base_name = base_image.replace(":", "-").replace("/", "-")
        
        # Create a valid Docker tag
        return f"function-runner-{base_name}-{cache_key}"


    def _prepare_image(self, base_image: str, requirements: List[str]) -> str:
        """Prepare and cache a Docker image with required packages"""
        cache_tag = self._get_cache_tag(base_image, requirements)
        
        try:
            # Check if cached image exists
            self.docker_client.images.get(cache_tag)
            logger.info(f"Using cached image: {cache_tag}")
            return cache_tag
        except docker.errors.ImageNotFound:
            logger.info(f"Creating new image from {base_image} with requirements: {requirements}")
            
            # Create Dockerfile for the prepared image
            dockerfile = f"""
            FROM {base_image}
            
            # Install cloudpickle and requirements
            RUN pip install --no-cache-dir cloudpickle {' '.join(requirements)}
            """
            
            # Build the image
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                (temp_path / 'Dockerfile').write_text(dockerfile)
                
                try:
                    image, _ = self.docker_client.images.build(
                        path=str(temp_path),
                        tag=cache_tag,
                        rm=True
                    )
                    logger.info(f"Successfully created cached image: {cache_tag}")
                    return cache_tag
                except Exception as e:
                    logger.error(f"Failed to create cached image: {e}")
                    raise

    def execute_function(
            self,
            folder_path: str,
            file_path: str,
            function_name: str,
            parameters: Dict[str, Any],
            requirements: List[str],
            env_vars: Dict[str, str],
            repo_name: str,
            base_image: str
        ) -> Any:
        """Execute a function in a Docker container using cached images"""
        try:
            # Get or create cached image
            image_tag = self._prepare_image(base_image, requirements)
            
            # Convert to absolute paths
            repo_path = Path(self.repo_service.get_repo_path(repo_name)).resolve()
            actions_path = Path(folder_path).resolve()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create execution script (no need for setup script anymore)
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

    # Add paths to sys.path
    repo_path = Path('/repo')
    action_path = Path('/actions')
    
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))
    if str(action_path) not in sys.path:
        sys.path.insert(0, str(action_path))
    
    # Set current working directory to repo path
    os.chdir(repo_path)
    
    # Get path to the module file
    module_file = action_path / '{file_path}'
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
        raise AttributeError(f"Function {function_name} not found in {{module_file}}")
        
    func = getattr(module, '{function_name}')
    
    # Load parameters
    with open('/data/params.json', 'r') as f:
        parameters = json.load(f)
    
    # Execute
    result = func(**parameters)
    
    # Save result
    with open('/data/result.json', 'wb') as f:
        cloudpickle.dump(result, f)
        
except Exception as e:
    import traceback
    with open('/data/error.txt', 'w') as f:
        f.write(traceback.format_exc())
    raise
"""
                # Write execution script and parameters
                (temp_path / 'exec.py').write_text(exec_script)
                with open(temp_path / 'params.json', 'w') as f:
                    json.dump(parameters, f)

                # Run in container using cached image
                try:
                    container = self.docker_client.containers.run(
                        image_tag,  # Use cached image
                        command=['python', '/data/exec.py'],  # No setup needed
                        volumes={
                            str(repo_path): {'bind': '/repo', 'mode': 'rw'},
                            str(actions_path): {'bind': '/actions', 'mode': 'ro'},
                            str(temp_path): {'bind': '/data', 'mode': 'rw'}
                        },
                        environment={
                            **env_vars,
                            'PYTHONUNBUFFERED': '1',
                        },
                        user=0,
                        detach=True
                    )

                    # Wait for container to finish and get logs
                    result = container.wait()
                    logs = container.logs().decode()
                    
                    if result['StatusCode'] != 0:
                        if (temp_path / 'error.txt').exists():
                            error_msg = (temp_path / 'error.txt').read_text()
                            raise ActionError(f"Function execution failed: {error_msg}")
                        raise ActionError(f"Container execution failed: {logs}")

                    # Load result
                    with open(temp_path / 'result.json', 'rb') as f:
                        return cloudpickle.load(f)

                finally:
                    # Cleanup container
                    try:
                        container.remove(force=True)
                    except:
                        pass

        except DockerException as e:
            raise ActionError(f"Docker error: {str(e)}")
        except Exception as e:
            raise ActionError(f"Error executing function: {str(e)}")

    def cleanup_cache(self):
        """Remove all cached images"""
        try:
            images = self.docker_client.images.list(filters={'reference': 'function-runner-*'})
            for image in images:
                self.docker_client.images.remove(image.id, force=True)
            logger.info("Cleaned up all cached images")
        except Exception as e:
            logger.error(f"Failed to cleanup cached images: {e}")






# if __name__ == "__main__":
#     import tempfile
#     import shutil
#     from pathlib import Path

#     # Test function to write in a temporary file
#     test_function_content = """
# def test_function(message: str, number: int):
#     '''Test function that creates a file and returns data
    
#     Args:
#         message: Message to write
#         number: Number to include
#     '''
#     # Write to a file in the repository
#     with open('test_output.txt', 'w') as f:
#         f.write(f"{message} - {number}")
    
#     # Return some data
#     return {
#         "message": message,
#         "number": number,
#         "doubled": number * 2
#     }
# """

#     try:
#         # Create temporary directories for testing
#         with tempfile.TemporaryDirectory() as repo_dir, \
#              tempfile.TemporaryDirectory() as actions_dir:
            
#             # Setup test repository
#             repo_path = Path(repo_dir)
#             actions_path = Path(actions_dir)

#             # Create test function file
#             with open(actions_path / "test_function.py", "w") as f:
#                 f.write(test_function_content)

#             # Create a mock RepoService
#             class MockRepoService:
#                 def get_repo_path(self, repo_name: str) -> str:
#                     return str(repo_path)

#             # Initialize services
#             repo_service = MockRepoService()
#             action_service = ActionService(repo_service)

#             print("Testing function execution...")
            
#             # First execution - will create cached image
#             print("\nFirst execution (creating cached image)...")
#             result1 = action_service.execute_function(
#                 folder_path=str(actions_path),
#                 file_path="test_function.py",
#                 function_name="test_function",
#                 parameters={
#                     "message": "Hello from Docker",
#                     "number": 42
#                 },
#                 requirements=["requests"],
#                 env_vars={"TEST_VAR": "test_value"},
#                 repo_name="test-repo",
#                 base_image="python:3.9-slim"  # Specify base image
#             )

#             print("\nFirst execution completed!")
#             print("Results:")
#             print(f"Returned data: {result1}")
            
#             # Check if file was created in repository
#             output_file = repo_path / "test_output.txt"
#             if output_file.exists():
#                 print(f"\nContent of created file:")
#                 print(output_file.read_text())
#             else:
#                 print("\nWarning: Output file was not created")

#             # Second execution - should use cached image
#             print("\nSecond execution (using cached image)...")
#             result2 = action_service.execute_function(
#                 folder_path=str(actions_path),
#                 file_path="test_function.py",
#                 function_name="test_function",
#                 parameters={
#                     "message": "Hello again from Docker",
#                     "number": 84
#                 },
#                 requirements=["requests"],  # Same requirements to use cached image
#                 env_vars={"TEST_VAR": "test_value"},
#                 repo_name="test-repo",
#                 base_image="python:3.9-slim"
#             )

#             print("\nSecond execution completed!")
#             print("Results:")
#             print(f"Returned data: {result2}")

#             # Test with different requirements (should create new cached image)
#             print("\nThird execution (with different requirements)...")
#             result3 = action_service.execute_function(
#                 folder_path=str(actions_path),
#                 file_path="test_function.py",
#                 function_name="test_function",
#                 parameters={
#                     "message": "Hello with new requirements",
#                     "number": 100
#                 },
#                 requirements=["requests", "pandas"],  # Different requirements
#                 env_vars={"TEST_VAR": "test_value"},
#                 repo_name="test-repo",
#                 base_image="python:3.9-slim"
#             )

#             print("\nThird execution completed!")
#             print("Results:")
#             print(f"Returned data: {result3}")

#             # Cleanup cached images
#             print("\nCleaning up cached images...")
#             action_service.cleanup_cache()

#     except Exception as e:
#         print(f"\nError during testing: {str(e)}")
#         # Print full traceback for debugging
#         import traceback
#         print("\nFull traceback:")
#         print(traceback.format_exc())