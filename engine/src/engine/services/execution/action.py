import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Callable, Optional
import cloudpickle

from engine.services.core.kit import Port
from engine.services.execution.function_parser import FunctionMetadata, FunctionParser
from engine.services.storage.repository import RepoService
from loguru import logger
import docker
import tempfile
from docker.errors import DockerException


class ActionError(Exception):
    """Base exception for action errors"""
    pass


class ActionService:
    def __init__(self, repo_service: RepoService):
        self.repo_service = repo_service
        self.docker_client = docker.from_env()
        self.cached_images = {}  # Cache for storing prepared images




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
        
        raise ActionError(f"No available ports found starting from {start_port}")

    def _execute_in_container(
        self,
        image_tag: str,
        temp_path: Path,
        volumes: Dict[str, Dict[str, str]],
        env_vars: Dict[str, str],
        ports: Optional[List[Port]] = None
    ) -> Any:
        """
        Execute the function in a Docker container and return the result.
        
        Args:
            image_tag: Docker image tag to use
            temp_path: Path to temporary directory containing execution files
            volumes: Volume mappings for Docker container
            env_vars: Environment variables for the container
            ports: Optional list of Port objects defining ports to expose
            
        Returns:
            Any: Result of the function execution
            
        Raises:
            ActionError: If there's an error during execution
        """
        try:
            # Convert ports to Docker port mapping format and find available ports
            port_bindings = {}
            port_env_vars = {}
            
            if ports:
                for port in ports:
                    # Find an available host port starting from the requested port
                    host_port = self._find_available_port(port.port)
                    
                    # Map container port to available host port
                    # Format: {container_port/protocol: (host_ip, host_port)}
                    port_bindings[f"{port.port}/tcp"] = host_port
                    
                    # Add port mapping to environment variables so the function knows
                    # which host ports were actually assigned
                    port_env_vars[f"PORT_{port.name.upper()}"] = str(host_port)
                    
                    logger.info(f"Mapping container port {port.port} ({port.name}) to host port {host_port}")

            container = self.docker_client.containers.run(
                image_tag,
                command=['python', '/data/exec.py'],
                volumes=volumes,
                environment={
                    **env_vars,
                    **port_env_vars,  # Add port mapping info to environment
                    'PYTHONUNBUFFERED': '1'
                },
                user=0,
                detach=True,
                ports=port_bindings,  # Add port mappings
                # Use bridge network mode with explicit port mappings
                network_mode="bridge"
            )

            try:
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
            ports: Optional[List[Port]] = None
        ) -> Any:
        """Execute a function from a file in a Docker container using cached images"""
        try:
            # Get or create cached image
            image_tag = self._prepare_image(base_image, requirements)
            
            # Convert to absolute paths
            repo_path = Path(self.repo_service.get_repo_path(repo_name)).resolve()
            actions_path = Path(folder_path).resolve()
            
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
                    ports=ports
                )

        except Exception as e:
            raise ActionError(f"Error executing function: {str(e)}")

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
                    env_vars=env_vars
                )

        except Exception as e:
            raise ActionError(f"Error executing function: {str(e)}")

#     def execute_function(
#             self,
#             folder_path: str,
#             file_path: str,
#             function_name: str,
#             parameters: Dict[str, Any],
#             requirements: List[str],
#             env_vars: Dict[str, str],
#             repo_name: str,
#             base_image: str
#         ) -> Any:
#         """Execute a function in a Docker container using cached images"""
#         try:
#             # Get or create cached image
#             image_tag = self._prepare_image(base_image, requirements)
            
#             # Convert to absolute paths
#             repo_path = Path(self.repo_service.get_repo_path(repo_name)).resolve()
#             actions_path = Path(folder_path).resolve()
            
#             with tempfile.TemporaryDirectory() as temp_dir:
#                 temp_path = Path(temp_dir)
                
#                 # Create execution script (no need for setup script anymore)
#                 exec_script = f"""
# import sys
# import json
# import cloudpickle
# import os
# from pathlib import Path
# import logging

# # Setup logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# try:
#     # Set environment variables
#     env_vars = {env_vars}
#     for key, value in env_vars.items():
#         os.environ[key] = str(value)

#     # Add paths to sys.path
#     repo_path = Path('/repo')
#     action_path = Path('/actions')
    
#     if str(repo_path) not in sys.path:
#         sys.path.insert(0, str(repo_path))
#     if str(action_path) not in sys.path:
#         sys.path.insert(0, str(action_path))
    
#     # Set current working directory to repo path
#     os.chdir(repo_path)
    
#     # Get path to the module file
#     module_file = action_path / '{file_path}'
#     logger.info(f"Loading module from: {{module_file}}")
    
#     if not module_file.exists():
#         raise FileNotFoundError(f"Module file not found: {{module_file}}")
    
#     # Import the module
#     import importlib.util
#     spec = importlib.util.spec_from_file_location('dynamic_module', str(module_file))
#     if spec is None:
#         raise ImportError(f"Could not find module: {{module_file}}")
        
#     module = importlib.util.module_from_spec(spec)
#     if spec.loader is None:
#         raise ImportError(f"Could not load module: {{module_file}}")
        
#     spec.loader.exec_module(module)
    
#     # Get and execute the function
#     if not hasattr(module, '{function_name}'):
#         raise AttributeError(f"Function {function_name} not found in {{module_file}}")
        
#     func = getattr(module, '{function_name}')
    
#     # Load parameters
#     with open('/data/params.json', 'r') as f:
#         parameters = json.load(f)
    
#     # Execute
#     result = func(**parameters)
    
#     # Save result
#     with open('/data/result.json', 'wb') as f:
#         cloudpickle.dump(result, f)
        
# except Exception as e:
#     import traceback
#     with open('/data/error.txt', 'w') as f:
#         f.write(traceback.format_exc())
#     raise
# """
#                 # Write execution script and parameters
#                 (temp_path / 'exec.py').write_text(exec_script)
#                 with open(temp_path / 'params.json', 'w') as f:
#                     json.dump(parameters, f)

#                 # Run in container using cached image
#                 try:
#                     container = self.docker_client.containers.run(
#                         image_tag,  # Use cached image
#                         command=['python', '/data/exec.py'],  # No setup needed
#                         volumes={
#                             str(repo_path): {'bind': '/repo', 'mode': 'rw'},
#                             str(actions_path): {'bind': '/actions', 'mode': 'ro'},
#                             str(temp_path): {'bind': '/data', 'mode': 'rw'}
#                         },
#                         environment={
#                             **env_vars,
#                             'PYTHONUNBUFFERED': '1',
#                         },
#                         user=0,
#                         detach=True
#                     )

#                     # Wait for container to finish and get logs
#                     result = container.wait()
#                     logs = container.logs().decode()
                    
#                     if result['StatusCode'] != 0:
#                         if (temp_path / 'error.txt').exists():
#                             error_msg = (temp_path / 'error.txt').read_text()
#                             raise ActionError(f"Function execution failed: {error_msg}")
#                         raise ActionError(f"Container execution failed: {logs}")

#                     # Load result
#                     with open(temp_path / 'result.json', 'rb') as f:
#                         return cloudpickle.load(f)

#                 finally:
#                     # Cleanup container
#                     try:
#                         container.remove(force=True)
#                     except:
#                         pass

#         except DockerException as e:
#             raise ActionError(f"Docker error: {str(e)}")
#         except Exception as e:
#             raise ActionError(f"Error executing function: {str(e)}")

#     def cleanup_cache(self):
#         """Remove all cached images"""
#         try:
#             images = self.docker_client.images.list(filters={'reference': 'function-runner-*'})
#             for image in images:
#                 self.docker_client.images.remove(image.id, force=True)
#             logger.info("Cleaned up all cached images")
#         except Exception as e:
#             logger.error(f"Failed to cleanup cached images: {e}")


