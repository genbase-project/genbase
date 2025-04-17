import os
import re
import time
import uuid
import socket
import tempfile
import subprocess
import sys
import ast
from typing import Any, Dict, Optional, Tuple, List
import docker.models
import docker.models.containers
import docker
from docker.errors import ContainerError, APIError, DockerException
from loguru import logger
from pathlib import Path
import venv
import importlib
import inspect
import json

from engine.const import RPC_PORT, VENV_BASE_DIR
from engine.services.agents.context import AgentContext
from engine.services.execution.function_parser import FunctionParser
from engine.services.storage.repository import RepoService
from engine.services.core.module import ModuleService, ModuleMetadata
from engine.services.core.kit import KitService, KitConfig
from engine.services.execution.state import AgentState, StateService


class AgentRunnerError(Exception):
    """Base exception for agent runner errors"""
    pass


class AgentRunnerService:
    """
    Service for running agents in isolated Docker containers using direct execution.
    
    This service:
    1. Creates and manages Docker containers based on kit configurations
    2. Passes context through environment variables
    3. Executes agent's process_request directly inside the container
    4. Handles cleanup and error scenarios
    """
    
    def __init__(
        self,
        repo_service: RepoService,
        module_service: ModuleService,
        state_service: StateService,
        kit_service: KitService,
        default_container_timeout: int = 600
    ):
        self.repo_service = repo_service
        self.module_service = module_service
        self.kit_service = kit_service
        self.state_service = state_service
        self.default_container_timeout = default_container_timeout
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise AgentRunnerError(f"Docker initialization failed: {e}")
        
        # Base path for virtual environments
        self.venvs_path = Path(os.path.abspath(VENV_BASE_DIR))
        os.makedirs(self.venvs_path, exist_ok=True)
        logger.info(f"Using virtual environments path: {self.venvs_path}")

    def _find_available_port(self, start_port: int = 9000, end_port: int = 9999) -> int:
        """Find an available port within the specified range."""
        for port in range(start_port, end_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:  # Port is available
                    return port
        raise AgentRunnerError(f"No available ports found between {start_port} and {end_port}")

    def execute_agent_profile(
        self,
        context: AgentContext,
        container_timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute an agent profile inside a Docker container using direct execution.
        
        Args:
            context: The agent context with module_id, profile, user_input, and session_id
            container_timeout: Optional timeout in seconds for container execution
            
        Returns:
            Dict containing the agent's response
            
        Raises:
            AgentRunnerError: If container creation or agent execution fails
        """
        # Generate a unique execution ID for this run
        exec_id = str(uuid.uuid4())
        container = None
        setup_script_path = None
        result_file_path = None
        
        try:
            # Get module metadata and kit config
            module_metadata = self.module_service.get_module_metadata(context.module_id)
            kit_config = self.module_service.get_module_kit_config(context.module_id)
            
            # Update module state to EXECUTING
            self.state_service.set_executing(context.module_id)
            
            # Prepare virtual environment for this kit if it doesn't exist
            venv_path = self._ensure_kit_venv(kit_config)
            
            # Create a temporary file to store results
            fd, result_file_path = tempfile.mkstemp(prefix="agent_result_", suffix=".json")
            os.close(fd)
            
            # Create and start the container
            container, setup_script_path = self._create_and_start_container(
                exec_id=exec_id,
                module_metadata=module_metadata,
                kit_config=kit_config,
                context=context,
                venv_path=venv_path,
                result_file_path=result_file_path,
                timeout=container_timeout or self.default_container_timeout
            )
            
            # Wait for container to complete
            result = {"response": "Agent execution failed or timed out.", "results": []}
            container.reload()
            
            # Keep checking until container exits or times out
            start_time = time.time()
            timeout = container_timeout or self.default_container_timeout
            while container.status == "running":
                if time.time() - start_time > timeout:
                    logger.warning(f"Container {container.short_id} timed out after {timeout}s")
                    container.stop(timeout=10)
                    raise AgentRunnerError(f"Container execution timed out after {timeout}s")
                time.sleep(1)
                container.reload()
            
            # Check container exit code
            if container.attrs.get('State', {}).get('ExitCode', -1) != 0:
                # Get container logs to diagnose the issue
                logs = container.logs().decode('utf-8', errors='replace')
                logger.error(f"Container {container.short_id} failed with exit code {container.attrs['State']['ExitCode']}")
                logger.error(f"Container logs:\n{logs}")
                raise AgentRunnerError(f"Container execution failed with exit code {container.attrs['State']['ExitCode']}")
            
            # Read results from file
            if os.path.exists(result_file_path) and os.path.getsize(result_file_path) > 0:
                try:
                    with open(result_file_path, 'r') as f:
                        result = json.load(f)
                except json.JSONDecodeError as e:
                    # If JSON is invalid, read raw content and log it
                    with open(result_file_path, 'r') as f:
                        raw_content = f.read()
                    logger.error(f"Invalid JSON result: {raw_content}")
                    raise AgentRunnerError(f"Invalid JSON result: {e}")
            else:
                # Get container logs if result file is empty/missing
                logs = container.logs().decode('utf-8', errors='replace')
                logger.error(f"No result file or empty result from container. Logs:\n{logs}")
                raise AgentRunnerError("No result returned from agent")
            
            # Update module state to STANDBY
            self.state_service.set_standby(context.module_id)
            
            return result
            
        except (ContainerError, APIError, DockerException) as docker_err:
            logger.error(f"Docker error during agent execution: {docker_err}", exc_info=True)
            self.state_service.set_standby(context.module_id)
            raise AgentRunnerError(f"Container error: {docker_err}")
            
        except Exception as e:
            logger.error(f"Unexpected error during agent execution: {e}", exc_info=True)
            self.state_service.set_standby(context.module_id)
            raise AgentRunnerError(f"Agent execution failed: {e}")
            
        finally:
            # Set KEEP_CONTAINERS=true for debugging
            keep_containers = os.getenv("DEV_MODE", False)
            
            # Remove container unless configured for reuse
            if container and not keep_containers:
                try:
                    container.remove(force=True)
                    logger.info(f"Container {container.short_id} removed")
                except Exception as e:
                    logger.warning(f"Error removing container {container.short_id}: {e}")
                    
            # Clean up temporary files
            for path in [setup_script_path, result_file_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e:
                        logger.warning(f"Error removing temporary file {path}: {e}")










    def _get_image_python_version(self, image_name: str) -> str:
        """
        Determine the Python version in a Docker image.
        
        Args:
            image_name: Docker image name/tag
            
        Returns:
            Python version as a string (e.g., "3.10", "3.11", "3.12")
        """
        try:
            # Run a simple container to get Python version
            cmd = [
                "docker", "run", "--rm", image_name,
                "python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            version = result.stdout.strip()
            
            # Validate version format
            if not re.match(r'^\d+\.\d+$', version):
                raise ValueError(f"Invalid Python version format: {version}")
                
            return version
            
        except subprocess.CalledProcessError as e:
            # The image might not have Python installed, or it might be at a different path
            logger.warning(f"Error getting Python version from image: {e}")
            logger.warning(f"Stdout: {e.stdout}, Stderr: {e.stderr}")
            
            # Try with python3 explicitly
            try:
                cmd = [
                    "docker", "run", "--rm", image_name,
                    "python3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                version = result.stdout.strip()
                
                if not re.match(r'^\d+\.\d+$', version):
                    raise ValueError(f"Invalid Python version format: {version}")
                    
                return version
                
            except Exception as inner_e:
                logger.error(f"Error getting Python version with python3: {inner_e}")
                raise ValueError(f"Could not determine Python version for image {image_name}")
        
        except Exception as e:
            logger.error(f"Unexpected error determining Python version: {e}")
            raise

    def _ensure_kit_venv(self, kit_config: KitConfig) -> Path:
        """Create a virtual environment for this kit if it doesn't exist and install dependencies."""
        # Determine the Python version in the Docker image
        try:
            python_version = self._get_image_python_version(kit_config.image)
            logger.info(f"Detected Python {python_version} in image {kit_config.image}")
        except Exception as e:
            logger.warning(f"Could not determine Python version from image: {e}")
            python_version = "3.12"  # Default if version detection fails
            logger.info(f"Using default Python version: {python_version}")
        
        # Generate a unique identifier for this kit version that includes Python version
        kit_id = f"{kit_config.owner}_{kit_config.id}_{kit_config.version}_py{python_version}"
        venv_path = self.venvs_path / kit_id
        
        # Check if venv already exists for this specific Python version
        if os.path.exists(os.path.join(venv_path, "bin", "python")) or os.path.exists(os.path.join(venv_path, "Scripts", "python.exe")):
            logger.info(f"Using existing virtual environment for kit {kit_id} with Python {python_version} - {venv_path}")
            return venv_path
        
        # Create virtual environment with host Python
        logger.info(f"Creating virtual environment for kit {kit_id} with Python {python_version}")
        try:
            # Create the virtual environment
            venv.create(venv_path, with_pip=True)
            
            # Get pip path
            pip_path = os.path.join(venv_path, "bin", "pip") if os.path.exists(os.path.join(venv_path, "bin", "pip")) else os.path.join(venv_path, "Scripts", "pip.exe")
            
            # Store Python version in a file for future reference
            version_file = venv_path / "python_version.txt"
            with open(version_file, 'w') as f:
                f.write(f"Python {python_version}")
            
            # Install genbase-client first
            subprocess.run([pip_path, "install", "genbase-client"], check=True)
            
            # Install kit dependencies
            if kit_config.dependencies:
                logger.info(f"Installing kit dependencies: {kit_config.dependencies}")
                subprocess.run([pip_path, "install"] + kit_config.dependencies, check=True)
            
            return venv_path
            
        except Exception as e:
            logger.error(f"Error creating virtual environment for kit {kit_id}: {e}")
            raise AgentRunnerError(f"Failed to create virtual environment: {e}")

    def _get_agent_class_for_profile(self, kit_config: KitConfig, profile: str) -> str:
        """Get the agent class name for a profile from the kit configuration."""
        try:
            if profile not in kit_config.profiles:
                raise AgentRunnerError(f"Profile '{profile}' not found in kit config")
                
            agent_name = kit_config.profiles[profile].agent
            
            # Find the agent class name from the agents list
            for agent in kit_config.agents:
                if agent.name == agent_name:
                    return agent.class_name
                    
            raise AgentRunnerError(f"Agent '{agent_name}' not found in kit config")
            
        except Exception as e:
            if isinstance(e, AgentRunnerError):
                raise
            raise AgentRunnerError(f"Error getting agent class for profile '{profile}': {e}")

    def _create_and_start_container(
        self,
        exec_id: str,
        module_metadata: ModuleMetadata,
        kit_config: KitConfig,
        context: AgentContext,
        venv_path: Path,
        result_file_path: str,
        timeout: int
    ) -> tuple[docker.models.containers.Container, str]:
        """Create and start a Docker container for the agent."""
        # Generate a unique container name
        container_name = f"genbase_agent_{module_metadata.module_id}_{context.profile}_{exec_id[:8]}"
        
        # Get paths for volume mounts and ensure they are absolute
        module_path = os.path.abspath(self.module_service.get_module_path(module_metadata.module_id))
        repo_path = os.path.abspath(self.repo_service.get_repo_path(module_metadata.repo_name))
        result_path = os.path.abspath(result_file_path)
        
        logger.debug(f"Module path: {module_path}")
        logger.debug(f"Repo path: {repo_path}")
        logger.debug(f"Result path: {result_path}")
        
        # Get the agent class name for this profile
        agent_class_name = self._get_agent_class_for_profile(kit_config, context.profile)
        logger.info(f"Agent class for profile '{context.profile}': {agent_class_name}")
        
        # Create a setup script that runs the specific agent
        setup_script = f"""#!/bin/bash
set -e

# Print environment and status information
echo "======= ENVIRONMENT ======="
hostname
python --version
pwd
env | sort


PY_VERSION=$(python -c "import sys; print(f'{{sys.version_info.major}}.{{sys.version_info.minor}}')")
echo "Detected Python version: $PY_VERSION"
export PYTHONPATH=/venv/lib/python$PY_VERSION/site-packages:/venv/lib/python3.12/site-packages:/venv/lib/python3.11/site-packages:/venv/lib/python3.10/site-packages:$PYTHONPATH
echo "PYTHONPATH: $PYTHONPATH"


# Create agent runner script
cat > /tmp/run_agent.py << 'EOL'
import os
import sys
import json
import traceback
import importlib
import importlib.util
import asyncio
from pathlib import Path

# Add paths to Python path
sys.path.insert(0, '/module')

# Get environment variables
MODULE_ID = os.environ.get("AGENT_MODULE_ID", "")
PROFILE = os.environ.get("AGENT_PROFILE", "")
USER_INPUT = os.environ.get("AGENT_USER_INPUT", "")
SESSION_ID = os.environ.get("AGENT_SESSION_ID", "")
AGENT_CLASS_NAME = os.environ.get("AGENT_CLASS_NAME", "")
RESULT_FILE_PATH = os.environ.get("RESULT_FILE_PATH", "/tmp/result.json")
RPYC_HOST = os.environ.get("RPYC_HOST", "host.docker.internal")
INTERNAL_RPYC_PORT = os.environ.get("INTERNAL_RPYC_PORT", {RPC_PORT})
# Import the genbase_client
try:
    from genbase_client import AgentContext
except ImportError:
    print("Error: genbase_client not found. Falling back to minimal implementation.")
    class AgentContext:
        def __init__(self, module_id="", profile="", user_input="", session_id=""):
            self.module_id = module_id
            self.profile = profile
            self.user_input = user_input
            self.session_id = session_id

def find_and_import_agent(agent_class_name):

    
    # Add module path to Python path for importing
    if '/module' not in sys.path:
        sys.path.insert(0, '/module')
    

    try:
        import os
        if os.path.exists('/module/agents'):
            
            # Check if __init__.py exists and print its content
            init_path = '/module/agents/__init__.py'

            
            # Check if git_ops_agent.py exists
            file_path = '/module/agents/git_ops_agent.py'

    except Exception as e:
        print(f"Error checking directories: {{e}}")
    
    # Approach 1: Try direct import from agents package
    try:
        import agents
        print(f"Available in agents: {{dir(agents)}}")
        
        if hasattr(agents, agent_class_name):
            print(f"Found {agent_class_name} in agents")
            return getattr(agents, agent_class_name)
    except ImportError as e:
        print(f"ImportError: {{e}}")
    except Exception as e:
        print(f"Error: {{e}}")
    
    # Approach 2: Manual import from __init__.py
    try:
        spec = importlib.util.spec_from_file_location("agents", "/module/agents/__init__.py")
        if spec:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"Loaded module from __init__.py, contents: {{dir(module)}}")
            
            if hasattr(module, agent_class_name):
                print(f"Found {agent_class_name} in __init__.py module")
                return getattr(module, agent_class_name)
    except Exception as e:
        print(f"Error importing from __init__.py: {{e}}")


async def run_agent():
    try:
        print(f"Processing request for {{MODULE_ID}}/{{PROFILE}}")
        
        # Create agent context
        ctx = AgentContext(
            module_id=MODULE_ID,
            profile=PROFILE,
            user_input=USER_INPUT,
            session_id=SESSION_ID
        )
        
        # Find and import the agent class
        agent_class = find_and_import_agent(AGENT_CLASS_NAME)
        if not agent_class:
            raise ImportError(f"Could not find {{AGENT_CLASS_NAME}} in any module")
        
        print(f"Found agent class: {{agent_class.__name__}}")
        
        # Instantiate the agent
        agent = agent_class(ctx)
        print(f"Instantiated agent: {{type(agent).__name__}}")
        
        # Check if process_request is async
        result = None
        if asyncio.iscoroutinefunction(agent.process_request):
            print("process_request is async, awaiting it")
            result = await agent.process_request()
        else:
            print("process_request is synchronous")
            result = agent.process_request()
        
        # Ensure result is in expected format
        if not isinstance(result, dict):
            result = {{"response": str(result), "results": []}}
        
        if "response" not in result:
            result["response"] = "No response content"
        
        if "results" not in result:
            result["results"] = []
        
        print(f"Agent result: {{result}}")
        
        # Write result to file
        with open(RESULT_FILE_PATH, 'w') as f:
            json.dump(result, f)
        print(f"Result written to {{RESULT_FILE_PATH}}")
        
    except Exception as e:
        print(f"Error processing request: {{e}}")
        traceback.print_exc()
        error_result = {{"response": f"Error: {{str(e)}}", "results": []}}
        with open(RESULT_FILE_PATH, 'w') as f:
            json.dump(error_result, f)

# Run the agent with proper async handling
if __name__ == "__main__":
    if sys.version_info >= (3, 7):
        asyncio.run(run_agent())
    else:
        # For Python 3.6 compatibility
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_agent())
EOL

# Run the agent
echo "======= STARTING AGENT ======="
python /tmp/run_agent.py
echo "Agent execution completed"
"""
        
        # Write setup script to a temporary file
        fd, setup_script_path = tempfile.mkstemp(prefix="agent_setup_", suffix=".sh")
        with os.fdopen(fd, 'w') as f:
            f.write(setup_script)
        os.chmod(setup_script_path, 0o755)  # Make executable
        
        # Set environment variables for the container
        env_vars = {
            # Base environment variables
            "DEBUG": os.getenv("DEBUG", "True"),  # Enable debug mode by default
            "BASE_URL": os.getenv("BASE_URL", "http://host.docker.internal:8000"),
            "PYTHONDONTWRITEBYTECODE": "1",  # Don't write .pyc files
            "PYTHONUNBUFFERED": "1",         # Don't buffer stdout/stderr
            
            # Agent Context
            "AGENT_MODULE_ID": context.module_id,
            "AGENT_PROFILE": context.profile,
            "AGENT_USER_INPUT": context.user_input,
            "AGENT_SESSION_ID": context.session_id or str(uuid.UUID(int=0)),
            
            # Agent class to load
            "AGENT_CLASS_NAME": agent_class_name,
            
            # Result file path 
            "RESULT_FILE_PATH": "/result.json",
            "RPYC_HOST": "host.docker.internal",
            "INTERNAL_RPYC_PORT": RPC_PORT,
              "RPYC_PORT": RPC_PORT,
            # Kit dependencies as a string
            "KIT_DEPENDENCIES": " ".join(kit_config.dependencies) if kit_config.dependencies else "",
            
            # Module specific environment variables
            **module_metadata.env_vars
        }
        
        # Configure Docker volume mounts with absolute paths
        volumes = {
            repo_path: {'bind': '/repo', 'mode': 'rw'},
            module_path: {'bind': '/module', 'mode': 'ro'},
            str(venv_path): {'bind': '/venv', 'mode': 'rw'},
            setup_script_path: {'bind': '/setup.sh', 'mode': 'ro'},
            result_path: {'bind': '/result.json', 'mode': 'rw'},
        }
        
        # Add additional port mappings from kit configuration if needed
        ports = {}
        if kit_config.ports:
            for port_config in kit_config.ports:
                port_num = port_config.port
                ports[f"{port_num}/tcp"] = self._find_available_port(port_num, port_num + 1000)

        # Create and start the container
        logger.info(f"Creating container {container_name} with image {kit_config.image}")
        try:
            container = self.docker_client.containers.run(
                image=kit_config.image,  # Use the kit's image
                name=container_name,
                command=["/bin/bash", "/setup.sh"],  # Use the setup script
                detach=True,
                environment=env_vars,
                volumes=volumes,
                ports=ports,
                network_mode="bridge",
                labels={
                    'exec_id': exec_id,
                    'module_id': context.module_id,
                    'profile': context.profile
                },
                extra_hosts={"host.docker.internal": "host-gateway"},
                working_dir="/repo"
            )
            
            logger.info(f"Container {container.short_id} started with agent runner")
            
            return container, setup_script_path
            
        except (ContainerError, APIError, DockerException) as e:
            logger.error(f"Failed to create or start container: {e}")
            raise AgentRunnerError(f"Container creation failed: {e}")
        





















    def get_agent_tools_schema(
        self,
        module_id: str,
        profile: str
    ) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible schema for all tools with @tool decorator in an agent
        without running a container.
        
        Args:
            module_id: The module ID
            profile: The profile to examine
            
        Returns:
            List of tool schemas in OpenAI function calling format
        """
        try:
            # Get module metadata and kit config
            module_metadata = self.module_service.get_module_metadata(module_id)
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            # Get the agent class name for this profile
            agent_class_name = self._get_agent_class_for_profile(kit_config, profile)
            
            # Get the module path
            module_path = self.module_service.get_module_path(module_id)
            
            # Find agent file - first check in agents/__init__.py
            init_path = Path(module_path) / "agents" / "__init__.py"
            agent_file = None
            agent_tools = []
            
            if init_path.exists():
                with open(init_path, 'r') as f:
                    file_content = f.read()
                    
                # Parse the file to find tools with @tool decorator
                tree = ast.parse(file_content)
                
                # Look for classes matching the agent_class_name
                class_finder = AgentClassFinder(agent_class_name)
                class_finder.visit(tree)
                
                if class_finder.found:
                    # Extract all methods with @tool decorator
                    for method_name in class_finder.tool_methods:
                        # Parse function details
                        func_parser = FunctionParser(method_name)
                        func_parser.visit(tree)
                        
                        if func_parser.found:
                            agent_tools.append({
                                "type": "function",
                                "function": {
                                    "name": method_name,
                                    "description": func_parser.description,
                                    "parameters": func_parser.parameters
                                }
                            })
            
            # If not found in __init__.py, check individual files
            if not agent_tools:
                agents_dir = Path(module_path) / "agents"
                if agents_dir.exists() and agents_dir.is_dir():
                    for py_file in agents_dir.glob("*.py"):
                        if py_file.name == "__init__.py":
                            continue
                            
                        with open(py_file, 'r') as f:
                            file_content = f.read()
                            
                        # Parse the file to find tools with @tool decorator
                        tree = ast.parse(file_content)
                        
                        # Look for classes matching the agent_class_name
                        class_finder = AgentClassFinder(agent_class_name)
                        class_finder.visit(tree)
                        
                        if class_finder.found:
                            # Extract all methods with @tool decorator
                            for method_name in class_finder.tool_methods:
                                # Parse function details
                                func_parser = FunctionParser(method_name)
                                func_parser.visit(tree)
                                
                                if func_parser.found:
                                    agent_tools.append({
                                        "type": "function",
                                        "function": {
                                            "name": method_name,
                                            "description": func_parser.description,
                                            "parameters": func_parser.parameters
                                        }
                                    })
                            break  # Found the agent class, no need to check other files
            
            return agent_tools
                
        except Exception as e:
            logger.error(f"Error getting agent tools schema: {e}", exc_info=True)
            raise AgentRunnerError(f"Failed to get agent tools schema: {e}")


    def execute_agent_tool(
        self,
        module_id: str,
        profile: str,
        tool_name: str,
        parameters: Dict[str, Any],
        container_timeout: Optional[int] = None
    ) -> Any:
        """
        Execute a specific tool from an agent in a Docker container.
        
        Args:
            module_id: The module ID
            profile: The profile to use
            tool_name: The name of the tool to execute
            parameters: The parameters to pass to the tool
            container_timeout: Optional timeout in seconds for container execution
            
        Returns:
            The result of the tool execution
        """
        # Generate a unique execution ID for this run
        exec_id = str(uuid.uuid4())
        container = None
        setup_script_path = None
        input_file_path = None
        output_file_path = None
        

        # Get module metadata and kit config
        module_metadata = self.module_service.get_module_metadata(module_id)
        kit_config = self.module_service.get_module_kit_config(module_id)
        
        # Prepare virtual environment for this kit if it doesn't exist
        venv_path = self._ensure_kit_venv(kit_config)
        
        # Create temporary files for input and output
        fd_in, input_file_path = tempfile.mkstemp(prefix="agent_tool_input_", suffix=".json")
        with os.fdopen(fd_in, 'w') as f:
            json.dump(parameters, f)
        
        fd_out, output_file_path = tempfile.mkstemp(prefix="agent_tool_output_", suffix=".json")
        os.close(fd_out)
        
        # Get the agent class name for this profile
        agent_class_name = self._get_agent_class_for_profile(kit_config, profile)
        
        # Create a simplified context for tool execution
        context = AgentContext(
            module_id=module_id,
            profile=profile,
            user_input="",  # Not needed for direct tool execution
            session_id=str(uuid.uuid4())
        )
        
        # Create a setup script that runs just the specific tool
        setup_script = f"""#!/bin/bash
set -e

# Print environment and status information
echo "======= ENVIRONMENT ======="
hostname
python --version
pwd
env | sort


PY_VERSION=$(python -c "import sys; print(f'{{sys.version_info.major}}.{{sys.version_info.minor}}')")
echo "Detected Python version: $PY_VERSION"

export PYTHONPATH=/venv/lib/python$PY_VERSION/site-packages:/venv/lib/python3.12/site-packages:/venv/lib/python3.11/site-packages:/venv/lib/python3.10/site-packages:$PYTHONPATH
echo "PYTHONPATH: $PYTHONPATH"


# Create tool runner script
cat > /tmp/run_tool.py << 'EOL'
import os
import sys
import json
import traceback
import importlib
import importlib.util
import asyncio
from pathlib import Path

# Add paths to Python path
sys.path.insert(0, '/module')

# Get environment variables
MODULE_ID = os.environ.get("AGENT_MODULE_ID", "")
PROFILE = os.environ.get("AGENT_PROFILE", "")
SESSION_ID = os.environ.get("AGENT_SESSION_ID", "")
AGENT_CLASS_NAME = os.environ.get("AGENT_CLASS_NAME", "")
TOOL_NAME = os.environ.get("TOOL_NAME", "")
INPUT_FILE_PATH = os.environ.get("INPUT_FILE_PATH", "/input.json")
OUTPUT_FILE_PATH = os.environ.get("OUTPUT_FILE_PATH", "/output.json")
RPYC_HOST = os.environ.get("RPYC_HOST", "host.docker.internal")
INTERNAL_RPYC_PORT = os.environ.get("INTERNAL_RPYC_PORT", "18861")

# Import the genbase_client
try:
    from genbase_client import AgentContext
except ImportError:
    print("Error: genbase_client not found. Falling back to minimal implementation.")
    class AgentContext:
        def __init__(self, module_id="", profile="", user_input="", session_id=""):
            self.module_id = module_id
            self.profile = profile
            self.user_input = user_input
            self.session_id = session_id

def find_and_import_agent(agent_class_name):
    
    # Add module path to Python path for importing
    if '/module' not in sys.path:
        sys.path.insert(0, '/module')
    
    # Approach 1: Try direct import from agents package
    try:
        import agents
        print(f"Available in agents: {{dir(agents)}}")
        
        if hasattr(agents, agent_class_name):
            print(f"Found {{agent_class_name}} in agents")
            return getattr(agents, agent_class_name)
    except ImportError as e:
        print(f"ImportError: {{e}}")
    except Exception as e:
        print(f"Error: {{e}}")
    
    # Approach 2: Manual import from __init__.py
    try:
        spec = importlib.util.spec_from_file_location("agents", "/module/agents/__init__.py")
        if spec:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"Loaded module from __init__.py, contents: {{dir(module)}}")
            
            if hasattr(module, agent_class_name):
                print(f"Found {{agent_class_name}} in __init__.py module")
                return getattr(module, agent_class_name)
    except Exception as e:
        print(f"Error importing from __init__.py: {{e}}")
    
    # Approach 3: Try individual python files
    try:
        agents_dir = Path('/module/agents')
        if agents_dir.exists():
            for py_file in agents_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                
                try:
                    name = py_file.stem
                    spec = importlib.util.spec_from_file_location(f"agents.{{name}}", py_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, agent_class_name):
                            print(f"Found {{agent_class_name}} in {{py_file}}")
                            return getattr(module, agent_class_name)
                except Exception as e:
                    print(f"Error importing {{py_file}}: {{e}}")
    except Exception as e:
        print(f"Error scanning agent files: {{e}}")
    
    return None

async def run_tool():
    try:
        print(f"Executing tool {{TOOL_NAME}} for {{MODULE_ID}}/{{PROFILE}}")
        
        # Create agent context
        ctx = AgentContext(
            module_id=MODULE_ID,
            profile=PROFILE,
            user_input="",  # Not needed for direct tool execution
            session_id=SESSION_ID
        )
        
        # Find and import the agent class
        agent_class = find_and_import_agent(AGENT_CLASS_NAME)
        if not agent_class:
            raise ImportError(f"Could not find {{AGENT_CLASS_NAME}} in any module")
        
        print(f"Found agent class: {{agent_class.__name__}}")
        
        # Instantiate the agent
        agent = agent_class(ctx)
        print(f"Instantiated agent: {{type(agent).__name__}}")
        
        # Load input parameters
        with open(INPUT_FILE_PATH, 'r') as f:
            parameters = json.load(f)
        
        # Get the tool method
        if not hasattr(agent, TOOL_NAME):
            raise AttributeError(f"Agent does not have a tool named {{TOOL_NAME}}")
        
        tool_method = getattr(agent, TOOL_NAME)
        print(f"Found tool method: {{TOOL_NAME}}")
        
        # Execute the tool
        result = None
        if asyncio.iscoroutinefunction(tool_method):
            print(f"Tool {{TOOL_NAME}} is async, awaiting it")
            result = await tool_method(**parameters)
        else:
            print(f"Tool {{TOOL_NAME}} is synchronous")
            result = tool_method(**parameters)
        
        print(f"Tool result: {{result}}")
        
        # Write result to file
        with open(OUTPUT_FILE_PATH, 'w') as f:
            json.dump(result, f)
        print(f"Result written to {{OUTPUT_FILE_PATH}}")
        
    except Exception as e:
        print(f"Error executing tool: {{e}}")
        traceback.print_exc()
        error_result = {{"error": f"Error: {{str(e)}}"}}
        with open(OUTPUT_FILE_PATH, 'w') as f:
            json.dump(error_result, f)

# Run the tool with proper async handling
if __name__ == "__main__":
    if sys.version_info >= (3, 7):
        asyncio.run(run_tool())
    else:
        # For Python 3.6 compatibility
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_tool())
EOL

# Run the tool
echo "======= EXECUTING TOOL ======="
python /tmp/run_tool.py
echo "Tool execution completed"
"""
        
        # Write setup script to a temporary file
        fd, setup_script_path = tempfile.mkstemp(prefix="tool_setup_", suffix=".sh")
        with os.fdopen(fd, 'w') as f:
            f.write(setup_script)
        os.chmod(setup_script_path, 0o755)  # Make executable
        
        # Set environment variables for the container
        env_vars = {
            # Base environment variables
            "DEBUG": os.getenv("DEBUG", "True"),  # Enable debug mode by default
            "BASE_URL": os.getenv("BASE_URL", "http://host.docker.internal:8000"),
            "PYTHONDONTWRITEBYTECODE": "1",  # Don't write .pyc files
            "PYTHONUNBUFFERED": "1",         # Don't buffer stdout/stderr
            
            # Agent/Tool Context
            "AGENT_MODULE_ID": module_id,
            "AGENT_PROFILE": profile,
            "AGENT_SESSION_ID": context.session_id,
            
            # Agent and tool specifics
            "AGENT_CLASS_NAME": agent_class_name,
            "TOOL_NAME": tool_name,
            
            # Input/Output file paths
            "INPUT_FILE_PATH": "/input.json",
            "OUTPUT_FILE_PATH": "/output.json",
            
            # RPyC settings for any needed engine communication
            "RPYC_HOST": "host.docker.internal",
            "INTERNAL_RPYC_PORT": str(RPC_PORT),
            
            # Module specific environment variables
            **module_metadata.env_vars
        }
        
        # Generate a unique container name
        container_name = f"genbase_tool_{module_id}_{profile}_{tool_name}_{exec_id[:8]}"
        
        # Get paths for volume mounts and ensure they are absolute
        module_path = os.path.abspath(self.module_service.get_module_path(module_id))
        repo_path = os.path.abspath(self.repo_service.get_repo_path(module_metadata.repo_name))
        
        # Configure Docker volume mounts with absolute paths
        volumes = {
            repo_path: {'bind': '/repo', 'mode': 'rw'},
            module_path: {'bind': '/module', 'mode': 'ro'},
            str(venv_path): {'bind': '/venv', 'mode': 'rw'},
            setup_script_path: {'bind': '/setup.sh', 'mode': 'ro'},
            input_file_path: {'bind': '/input.json', 'mode': 'ro'},
            output_file_path: {'bind': '/output.json', 'mode': 'rw'},
        }
        
        # Create and start the container
        logger.info(f"Creating container {container_name} with image {kit_config.image} to execute tool {tool_name}")
        try:
            container = self.docker_client.containers.run(
                image=kit_config.image,  # Use the kit's image
                name=container_name,
                command=["/bin/bash", "/setup.sh"],  # Use the setup script
                detach=True,
                environment=env_vars,
                volumes=volumes,
                network_mode="bridge",
                labels={
                    'exec_id': exec_id,
                    'module_id': module_id,
                    'profile': profile,
                    'tool_name': tool_name
                },
                extra_hosts={"host.docker.internal": "host-gateway"},
                working_dir="/repo"
            )
            
            logger.info(f"Container {container.short_id} started for tool execution")
            
            # Wait for container to complete
            start_time = time.time()
            timeout = container_timeout or self.default_container_timeout
            
            while True:
                container.reload()
                if container.status != "running":
                    break
                    
                if time.time() - start_time > timeout:
                    logger.warning(f"Container {container.short_id} timed out after {timeout}s")
                    container.stop(timeout=10)
                    raise AgentRunnerError(f"Tool execution timed out after {timeout}s")
                    
                time.sleep(1)
            
            # Check container exit code
            if container.attrs.get('State', {}).get('ExitCode', -1) != 0:
                # Get container logs to diagnose the issue
                logs = container.logs().decode('utf-8', errors='replace')
                logger.error(f"Container {container.short_id} failed with exit code {container.attrs['State']['ExitCode']}")
                logger.error(f"Container logs:\n{logs}")
                raise AgentRunnerError(f"Tool execution failed with exit code {container.attrs['State']['ExitCode']}")
            
            # Read results from file
            if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                try:
                    with open(output_file_path, 'r') as f:
                        result = json.load(f)
                    return result
                except json.JSONDecodeError as e:
                    # If JSON is invalid, read raw content and log it
                    with open(output_file_path, 'r') as f:
                        raw_content = f.read()
                    logger.error(f"Invalid JSON result: {raw_content}")
                    raise AgentRunnerError(f"Invalid JSON result from tool execution: {e}")
            else:
                # Get container logs if result file is empty/missing
                logs = container.logs().decode('utf-8', errors='replace')
                logger.error(f"No output file or empty result from container. Logs:\n{logs}")
                raise AgentRunnerError("No result returned from tool execution")
                
        except (ContainerError, APIError, DockerException) as docker_err:
            logger.error(f"Docker error during tool execution: {docker_err}", exc_info=True)
            raise AgentRunnerError(f"Container error: {docker_err}")
            
        except Exception as e:
            logger.error(f"Unexpected error during tool execution: {e}", exc_info=True)
            raise AgentRunnerError(f"Tool execution failed: {e}")
            
        finally:
            # Set KEEP_CONTAINERS=true for debugging
            keep_containers = os.getenv("DEV_MODE", False)
            
            # Remove container unless configured for reuse
            if container and not keep_containers:
                try:
                    container.remove(force=True)
                    logger.info(f"Container {container.short_id} removed")
                except Exception as e:
                    logger.warning(f"Error removing container {container.short_id}: {e}")
                    
            # Clean up temporary files
            for path in [setup_script_path, input_file_path, output_file_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e:
                        logger.warning(f"Error removing temporary file {path}: {e}")




# Add this helper class for finding agent classes and their tool methods
class AgentClassFinder(ast.NodeVisitor):
    """AST visitor to find a specific agent class and its tool-decorated methods"""
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.found = False
        self.tool_methods = set()
        self._current_class = None
        self._decorator_tools = set()  # Track methods marked with @tool
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit a class definition"""
        old_class = self._current_class
        self._current_class = node.name
        
        if node.name == self.class_name:
            self.found = True
            
            # Check for @tool decorated methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if any decorator is named 'tool'
                    for decorator in item.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                            self.tool_methods.add(item.name)
                            break
        
        # Visit the class body to find base classes and nested classes
        self.generic_visit(node)
        self._current_class = old_class