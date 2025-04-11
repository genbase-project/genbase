import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Set, Callable, Optional
import cloudpickle
import docker.errors

from engine.services.core.api_key import ApiKeyService
from engine.services.core.kit import Port
from engine.services.execution.function_parser import FunctionMetadata, FunctionParser
from engine.services.storage.repository import RepoService
from loguru import logger
import docker
import tempfile
from docker.errors import DockerException

from docker.models.containers import Container

class ToolError(Exception):
    """Base exception for action errors"""
    pass

class WarmContainer:
    def __init__(self, container: Container, image_tag: str, last_used: datetime):
        self.container = container
        self.image_tag = image_tag
        self.last_used = last_used



class ToolService:
    def __init__(self, repo_service: RepoService, warm_container_timeout: int = 900):
        self.repo_service = repo_service
        self.docker_client = docker.from_env()
        self.cached_images = {}  # Cache for storing prepared images
        self.warm_containers = {}  # Dict to store warm containers by repo name
        self.warm_container_timeout = warm_container_timeout  # Timeout in seconds (default 5 minutes)
        self.cleanup_thread = threading.Thread(target=self._cleanup_warm_containers, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_warm_containers(self):
        """Background thread to cleanup expired warm containers"""
        while True:
            try:
                current_time = datetime.now()
                repos_to_remove = []

                for repo_name, warm_container in self.warm_containers.items():
                    if (current_time - warm_container.last_used).total_seconds() > self.warm_container_timeout:
                        try:
                            warm_container.container.remove(force=True)
                            logger.info(f"Removed expired warm container for repo: {repo_name}")
                            repos_to_remove.append(repo_name)
                        except Exception as e:
                            logger.error(f"Error removing warm container for repo {repo_name}: {e}")
                            repos_to_remove.append(repo_name)

                for repo_name in repos_to_remove:
                    self.warm_containers.pop(repo_name, None)

            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")

            time.sleep(60)  # Check every minute

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

            if parser.found:
                # Function was found directly in this file
                return FunctionMetadata(
                    name=function_name,
                    description=parser.description,
                    parameters=parser.parameters,
                    is_async=parser.is_async
                )
                
            # Function not found, check for imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and any(name.name == function_name for name in node.names):
                    # Found an import for our function
                    module_name = node.module
                    if module_name and module_name.startswith('.'):
                        # Relative import, resolve the path
                        current_dir = Path(file_path).parent
                        # Remove the leading dots and convert to path
                        rel_path = module_name.lstrip('.')
                        if rel_path:
                            # There's a module name after the dots
                            target_file = current_dir / f"{rel_path}.py"
                        else:
                            # Just dots, referring to the package/directory
                            target_file = current_dir / "__init__.py"
                    else:
                        # Absolute import, assuming it's within the folder_path
                        target_file = Path(module_name.replace('.', '/') + '.py')
                    
                    logger.info(f"Function {function_name} imported from {target_file}")
                    return self.get_function_metadata(folder_path, str(target_file), function_name)
                    
            # If we get here, the function wasn't found and wasn't imported
            raise ToolError(f"Function {function_name} not found in {file_path}")

        except Exception as e:
            logger.error(f"Error analyzing function: {str(e)}")
            raise ToolError(f"Error analyzing function: {str(e)}")
    

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


    def _create_execution_script(
        self,
        env_vars: Dict[str, str],
        is_file_based: bool = False,
        file_path: str = None,
        function_name: str = None
    ) -> str:
        """
        Create the Python execution script for the Docker container.
        
        Args:
            env_vars: Environment variables to set in the container
            is_file_based: Whether the execution is for a file-based function
            file_path: Path to the module file (only needed if is_file_based is True)
            function_name: Name of the function to execute (only needed if is_file_based is True)
            
        Returns:
            str: The Python script content
        """
        if is_file_based:
            function_loading_code = f"""
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
    
    # Get the function
    if not hasattr(module, '{function_name}'):
        raise AttributeError(f"Function {function_name} not found in {{module_file}}")
        
    function = getattr(module, '{function_name}')
"""
        else:
            function_loading_code = """
    # Load the function from pickle
    with open('/data/function.pkl', 'rb') as f:
        function = cloudpickle.load(f)
"""

        return f"""
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
    
{function_loading_code}
    
    # Load parameters
    with open('/data/params.json', 'r') as f:
        parameters = json.load(f)
    
    # Execute the function
    result = function(**parameters)
    
    # Save result
    with open('/data/result.json', 'wb') as f:
        cloudpickle.dump(result, f)
        
except Exception as e:
    import traceback
    with open('/data/error.txt', 'w') as f:
        f.write(traceback.format_exc())
    raise
"""

    def _find_available_port(self, start_port: int) -> int:
        """
        Find an available port starting from the given port number.
        
        Args:
            start_port: Initial port number to check
            
        Returns:
            int: First available port number
        """
        import socket
        
        current_port = start_port
        max_port = 65535
        
        while current_port <= max_port:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('', current_port))
                sock.listen(1)
                sock.close()
                return current_port
            except OSError:
                current_port += 1
            finally:
                sock.close()
        
        raise ToolError(f"No available ports found starting from {start_port}")

    def _execute_in_container(
        self,
        image_tag: str,
        temp_path: Path,
        volumes: Dict[str, Dict[str, str]],
        env_vars: Dict[str, str],
        ports: Optional[List[Port]] = None,
        repo_name: Optional[str] = None
    ) -> Any:
        """
        Execute the function in a Docker container and return the result.
        """
        try:
            # Check for existing warm container
            warm_container = None
            if repo_name:
                warm_container = self.warm_containers.get(repo_name)
                if warm_container and warm_container.image_tag == image_tag:
                    logger.info(f"Removing old warm container for repo: {repo_name}")
                    try:
                        warm_container.container.remove(force=True)
                    except Exception as e:
                        logger.error(f"Error removing old container: {e}")
                    warm_container = None

            # Create new container if needed
            if not warm_container:
                port_bindings = {}
                port_env_vars = {}
                
                if ports:
                    for port in ports:
                        host_port = self._find_available_port(port.port)
                        port_bindings[f"{port.port}/tcp"] = host_port
                        port_env_vars[f"PORT_{port.name.upper()}"] = str(host_port)
                        logger.info(f"Mapping container port {port.port} ({port.name}) to host port {host_port}")

                # Ensure volume paths exist in warm container
                container = self.docker_client.containers.run(
                    image_tag,
                    command=['tail', '-f', '/dev/null'],  # Keep container running
                    volumes=volumes,
                    environment={
                        **env_vars,
                        **port_env_vars,
                        'PYTHONUNBUFFERED': '1'
                    },
                    user=0,
                    detach=True,
                    ports=port_bindings,
                    network_mode="bridge",
                    privileged=True
                )
                
                # Ensure container is running before proceeding
                container.reload()

            try:
                # Execute function in container
                exec_result = container.exec_run(
                    cmd=['python', '/data/exec.py'],
                    environment={
                        **env_vars,
                        'PYTHONUNBUFFERED': '1'
                    }
                )

                if exec_result.exit_code != 0:
                    if (temp_path / 'error.txt').exists():
                        error_msg = (temp_path / 'error.txt').read_text()
                        raise ToolError(f"Function execution failed: {error_msg}")
                    raise ToolError(f"Container execution failed: {exec_result.output.decode()}")

                # Load result
                with open(temp_path / 'result.json', 'rb') as f:
                    result = cloudpickle.load(f)

                # Update or store warm container
                if repo_name:
                    self.warm_containers[repo_name] = WarmContainer(
                        container=container,
                        image_tag=image_tag,
                        last_used=datetime.now()
                    )
                else:
                    # If no repo_name, remove container immediately
                    container.remove(force=True)

                return result

            except Exception as e:
                # Clean up container on error if not keeping warm
                if not repo_name:
                    try:
                        container.remove(force=True)
                    except:
                        pass
                raise e

        except DockerException as e:
            raise ToolError(f"Docker error: {str(e)}")
        except Exception as e:
            raise ToolError(f"Error executing function: {str(e)}")



















    def resolve_function_location(
        self,
        folder_path: str,
        file_path: str,
        function_name: str
    ) -> str:
        """
        Resolve the actual file path where a function is defined.
        
        Args:
            folder_path: Base folder path
            file_path: Path to the file where the function is requested
            function_name: Name of the function to resolve
            
        Returns:
            str: Path to the file where the function is actually defined
        """
        logger.info(f"Resolving location for function {function_name} in {file_path}")
        
        try:
            full_path = Path(folder_path) / file_path
            logger.debug(f"Full path: {full_path}")

            # Read the source code
            with open(full_path, 'r') as f:
                source = f.read()
                logger.debug(f"Source code: {source}")

            # Parse using AST
            tree = ast.parse(source)
            parser = FunctionParser(function_name)
            parser.visit(tree)

            if parser.found:
                # Function was found directly in this file
                logger.info(f"Function {function_name} defined directly in {file_path}")
                return file_path
                
            # Function not found, check for imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and any(name.name == function_name for name in node.names):
                    # Found an import for our function
                    module_name = node.module
                    if module_name and module_name.startswith('.'):
                        # Relative import, resolve the path
                        current_dir = Path(file_path).parent
                        # Remove the leading dots and convert to path
                        rel_path = module_name.lstrip('.')
                        if rel_path:
                            # There's a module name after the dots
                            target_file = current_dir / f"{rel_path}.py"
                        else:
                            # Just dots, referring to the package/directory
                            target_file = current_dir / "__init__.py"
                    else:
                        # Absolute import, assuming it's within the folder_path
                        target_file = Path(module_name.replace('.', '/') + '.py')
                    
                    target_file_str = str(target_file)
                    logger.info(f"Function {function_name} imported from {target_file_str}")
                    # Recursively find the actual file
                    return self.resolve_function_location(folder_path, target_file_str, function_name)
                    
            # If we get here, the function wasn't found and wasn't imported
            raise ToolError(f"Function {function_name} not found in {file_path}")

        except Exception as e:
            logger.error(f"Error resolving function location: {str(e)}")
            raise ToolError(f"Error resolving function location: {str(e)}")
        


    def execute_function(
            self,
            folder_path: str,
            file_path: str,
            function_name: str,
            parameters: Dict[str, Any],
            requirements: List[str],
            env_vars: Dict[str, str],
            repo_name: str,
            base_image: str = "python:3.9-slim",
            ports: Optional[List[Port]] = None,
            module_id: Optional[str] = None
        ) -> Any:
        """Execute a function from a file in a Docker container using cached images"""
        try:
            # Get or create cached image
            image_tag = self._prepare_image(base_image, requirements)
            file_path = self.resolve_function_location(folder_path, file_path, function_name)

            # Convert to absolute paths
            repo_path = Path(self.repo_service.get_repo_path(repo_name)).resolve()
            actions_path = Path(folder_path).resolve()



            # Add gateway env vars
            if module_id:
                env_vars['GENBASE_GATEWAY_URL'] = os.getenv('BASE_URL').replace('http://localhost','http://host.docker.internal')+ "/api/v1" + "/gateway"
                api_key_service = ApiKeyService()
                api_key_obj = api_key_service.get_api_key(module_id, auto_create=True)
                module_api_key = api_key_obj.api_key
                logger.debug(f"Found API key for module {module_id}")

                env_vars['GENBASE_GATEWAY_API_KEY'] = module_api_key
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create execution script
                exec_script = self._create_execution_script(
                    env_vars=env_vars,
                    is_file_based=True,
                    file_path=file_path,
                    function_name=function_name
                )
                
                # Write execution script and parameters
                (temp_path / 'exec.py').write_text(exec_script)
                with open(temp_path / 'params.json', 'w') as f:
                    json.dump(parameters, f)

                # Setup volumes
                volumes = {
                    str(repo_path): {'bind': '/repo', 'mode': 'rw'},
                    str(actions_path): {'bind': '/actions', 'mode': 'ro'},
                    str(temp_path): {'bind': '/data', 'mode': 'rw'}
                }

                return self._execute_in_container(
                    image_tag=image_tag,
                    temp_path=temp_path,
                    volumes=volumes,
                    env_vars=env_vars,
                    ports=ports,
                    repo_name=repo_name
                )

        except Exception as e:
            raise ToolError(f"Error executing function: {str(e)}")

    def execute_direct_function(
        self,
        function: Callable,
        parameters: Dict[str, Any],
        requirements: List[str],
        env_vars: Dict[str, str],
        base_image: str = "python:3.9-slim"
    ) -> Any:
        """Execute a directly provided function in a Docker container using cached images"""
        try:
            # Get or create cached image
            image_tag = self._prepare_image(base_image, requirements)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Serialize the function using cloudpickle
                with open(temp_path / 'function.pkl', 'wb') as f:
                    cloudpickle.dump(function, f)
                
                # Create execution script
                exec_script = self._create_execution_script(
                    env_vars=env_vars,
                    is_file_based=False
                )

                # Write execution script and parameters
                (temp_path / 'exec.py').write_text(exec_script)
                with open(temp_path / 'params.json', 'w') as f:
                    json.dump(parameters, f)

                # Setup volumes
                volumes = {
                    str(temp_path): {'bind': '/data', 'mode': 'rw'}
                }

                return self._execute_in_container(
                    image_tag=image_tag,
                    temp_path=temp_path,
                    volumes=volumes,
                    env_vars=env_vars,
                    # No repo_name for direct functions
                    repo_name=None
                )

        except Exception as e:
            raise ToolError(f"Error executing function: {str(e)}")

