# genbase_client/agent_run_server.py

import os
import sys
import importlib
import inspect
import rpyc
import json
import asyncio
from typing import Dict, Any, Optional, Type
from rpyc.utils.server import ThreadedServer
from loguru import logger

# Import from the client library
from genbase_client import BaseAgent
from genbase_client.types import AgentContext


class AgentRunnerRPyCService(rpyc.Service):
    """
    RPyC service that runs inside the container and handles requests from the engine.
    Acts as the server-side endpoint for the AgentRunnerService's connections.
    """
    _agent_instance: Optional[BaseAgent] = None
    
    def on_connect(self, conn):
        logger.info(f"Engine connected to container's RPyC service: {conn}")
        # Configure connection security settings
        conn._config["allow_public_attrs"] = False
        conn._config["allow_pickle"] = False
        conn._config["allow_setattr"] = False
        conn._config["allow_delattr"] = False
    
    def on_disconnect(self, conn):
        logger.info(f"Engine disconnected from container's RPyC service: {conn}")
        # Clean up agent instance on disconnect if needed
        if self._agent_instance:
            try:
                self._agent_instance.close()  # Close RPyC connection from agent to engine
                self._agent_instance = None
            except Exception as e:
                logger.error(f"Error cleaning up agent instance: {e}")
    
    def _load_agent_class(self) -> Type[BaseAgent]:
        """
        Dynamically locate and load the agent class from the container's kit.
        
        The agent class should:
        1. Be a subclass of BaseAgent
        2. Be located in the /module/agents directory
        3. Match the agent_type specified in the kit.yaml
        """
        try:
            # Get agent type from environment or use default
            agent_profile = os.getenv("AGENT_PROFILE", "default")
            
            # Search for agent implementation in the /module/agents directory
            agents_dir = "/module/agents"
            
            # First, try to find agent file with matching name (agent_<profile>.py)
            agent_file = f"agent_{agent_profile}.py"
            agent_path = os.path.join(agents_dir, agent_file)
            
            if os.path.exists(agent_path):
                # Import from specific file
                spec = importlib.util.spec_from_file_location(f"dynamic_agent_{agent_profile}", agent_path)
                if not spec or not spec.loader:
                    raise ImportError(f"Failed to create module spec from {agent_path}")
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Try loading from __init__.py instead
                init_path = os.path.join(agents_dir, "__init__.py")
                if not os.path.exists(init_path):
                    raise ImportError(f"Neither {agent_path} nor {init_path} exists")
                
                spec = importlib.util.spec_from_file_location("dynamic_agents", init_path)
                if not spec or not spec.loader:
                    raise ImportError(f"Failed to create module spec from {init_path}")
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            # Find all BaseAgent subclasses in the module
            agent_classes = []
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                    agent_classes.append(obj)
            
            if not agent_classes:
                raise ImportError(f"No BaseAgent subclasses found in {module.__name__}")
            
            # Find the agent class with the matching agent_type
            for agent_class in agent_classes:
                # Create a temporary instance to check agent_type
                # Use a dummy context as we won't actually use this instance
                dummy_context = AgentContext(
                    module_id="dummy", profile="dummy", user_input="", session_id="dummy"
                )
                temp_instance = agent_class(dummy_context)
                
                if temp_instance.agent_type == agent_profile:
                    logger.info(f"Found matching agent class: {agent_class.__name__}")
                    return agent_class
            
            # If we reach here, try the first agent class regardless of type
            logger.warning(f"No agent with agent_type={agent_profile} found. Using {agent_classes[0].__name__}")
            return agent_classes[0]
            
        except Exception as e:
            logger.error(f"Error loading agent class: {e}", exc_info=True)
            raise ImportError(f"Failed to load agent class: {e}")
    
    def _create_agent_instance(self, context_dict: Dict[str, Any]) -> BaseAgent:
        """Create an instance of the agent class with the provided context."""
        try:
            # Create AgentContext from dict
            context = AgentContext(
                module_id=context_dict["module_id"],
                profile=context_dict["profile"],
                user_input=context_dict["user_input"],
                session_id=context_dict.get("session_id")
            )
            
            # Load the agent class
            agent_class = self._load_agent_class()
            
            # Create an instance of the agent
            logger.info(f"Creating instance of {agent_class.__name__} for {context.module_id}/{context.profile}")
            agent_instance = agent_class(context)
            
            # Store the instance for potential reuse or cleanup
            self._agent_instance = agent_instance
            
            return agent_instance
            
        except Exception as e:
            logger.error(f"Error creating agent instance: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create agent instance: {e}")
    
    def exposed_process_request(self, context_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request by creating an agent instance and calling its process_request method.
        This is the main entry point called by the engine via RPyC.
        """
        logger.info(f"Received process_request for {context_dict['module_id']}/{context_dict['profile']}")
        
        try:
            # Create agent instance
            agent = self._create_agent_instance(context_dict)
            
            # Run process_request
            logger.info(f"Calling process_request on {agent.__class__.__name__}")
            
            # Handle async process_request method
            if inspect.iscoroutinefunction(agent.process_request):
                # Run async method in event loop
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(agent.process_request())
            else:
                # Run synchronous method directly
                result = agent.process_request()
            
            # Convert result to dict if needed
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            elif not isinstance(result, dict):
                result = {"response": str(result), "results": []}
            
            logger.info(f"process_request completed successfully with response length: {len(str(result.get('response', '')))}")
            return result
            
        except Exception as e:
            logger.error(f"Error in process_request: {e}", exc_info=True)
            return {
                "response": f"Error executing agent: {str(e)}",
                "results": [],
                "error": str(e)
            }


def run_agent_server():
    """
    Start the RPyC server inside the container.
    This function is called as the container's entry point.
    """
    try:
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(sys.stderr, level="DEBUG" if os.getenv("DEBUG") else "INFO")
        
        logger.info("Starting Genbase Agent RPyC server...")
        
        # Get port from environment or use default
        port = int(os.getenv("CONTAINER_RPYC_PORT", 18862))
        
        # Create and start the RPyC server
        server = ThreadedServer(
            AgentRunnerRPyCService,
            port=port,
            hostname="0.0.0.0",  # Listen on all interfaces
            protocol_config={
                "allow_public_attrs": False,
                "allow_pickle": False,
                "sync_request_timeout": 300,  # 5 minute timeout
            }
        )
        
        logger.info(f"Agent RPyC server listening on port {port}")
        server.start()  # This blocks until the server is stopped
        
    except Exception as e:
        logger.error(f"Failed to start RPyC server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # This allows running the server directly for testing
    run_agent_server()