"""Agent plugin loader service."""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Type, Optional, Union

from engine.services.agents.base_agent import BaseAgent, AgentServices
from engine.config.workflow_config import WorkflowConfig
from engine.utils.logging import logger

class AgentLoaderError(Exception):
    """Base exception for agent loading errors"""
    pass

class AgentLoader:
    """Dynamically loads agent plugins from kits"""
    
    def __init__(self, agent_services: AgentServices):
        self.agent_services = agent_services
        self.loaded_agents: Dict[str, Type[BaseAgent]] = {}

    def get_agent(self, kit_path: Path, agent_name: str, class_name: str) -> BaseAgent:
        """
        Get agent instance, loading if necessary.

        Args:
            kit_path: Path to kit root directory
            agent_name: Name of agent from kit.yaml
            class_name: Name of agent class to load

        Returns:
            BaseAgent: Agent instance
            
        Raises:
            AgentLoaderError: If agent cannot be loaded
        """
        try:
            agents_dir = kit_path / "agents"
            if not agents_dir.exists():
                raise AgentLoaderError(f"Agents directory not found: {agents_dir}")

            # Create cache key 
            cache_key = f"{kit_path}:{agent_name}"

            # Return cached agent class if available
            if cache_key in self.loaded_agents:
                agent_class = self.loaded_agents[cache_key]
            else:
                # Import agent module
                module_path = agents_dir / f"{agent_name}.py"
                if not module_path.exists():
                    module_path = agents_dir / "__init__.py"

                if not module_path.exists():
                    raise AgentLoaderError(f"No agent module found for {agent_name}")

                # Create module spec
                spec = importlib.util.spec_from_file_location(
                    f"dynamic_agents_{kit_path.name}_{agent_name}",
                    str(module_path)
                )
                if not spec or not spec.loader:
                    raise AgentLoaderError(f"Failed to load module spec from {module_path}")

                # Load module
                module_name = f"dynamic_agents_{kit_path.name}_{agent_name}"
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Get agent class - first try in module
                if not hasattr(module, class_name):
                    # If not in kit module, try base.agents
                    try:
                        from base.agents import __all__ as base_agents
                        base_module = __import__('base.agents', fromlist=base_agents)
                        if hasattr(base_module, class_name):
                            agent_class = getattr(base_module, class_name)
                            if issubclass(agent_class, BaseAgent):
                                return agent_class(self.agent_services)
                    except ImportError:
                        pass
                    raise AgentLoaderError(f"Agent class {class_name} not found in {module_path} or base.agents")

                agent_class = getattr(module, class_name)
                if not issubclass(agent_class, BaseAgent):
                    raise AgentLoaderError(f"{class_name} in {module_path} is not a BaseAgent subclass")
                
                # Create instance to get agent_type value
                agent_instance = agent_class(self.agent_services)
                if agent_instance.agent_type != agent_name:
                    raise AgentLoaderError(f"Agent type mismatch: class {class_name} has agent_type '{agent_instance.agent_type}' but kit.yaml specifies '{agent_name}'")

                # Cache agent class
                self.loaded_agents[cache_key] = agent_class

            # Create and return agent instance
            return agent_class(self.agent_services)

        except Exception as e:
            raise AgentLoaderError(f"Failed to get agent {agent_name}: {str(e)}")

    def load_workflow_agent(
        self,
        kit_path: Path,
        workflow_name: str,
        workflow_config: Union[dict, WorkflowConfig]
    ) -> Optional[BaseAgent]:
        """
        Load agent for specific workflow based on kit.yaml config.

        Args:
            kit_path: Path to kit root directory
            workflow_name: Name of workflow
            workflow_config: Workflow configuration from kit.yaml

        Returns:
            Optional[BaseAgent]: Agent instance if agent is configured, None otherwise
            
        Raises:
            AgentLoaderError: If agent cannot be loaded
        """
        try:
            # Read kit.yaml
            with open(kit_path / "kit.yaml") as f:
                import yaml
                kit_config = yaml.safe_load(f)

            # Convert WorkflowConfig to dict if needed
            if isinstance(workflow_config, WorkflowConfig):
                workflow_config = {"agent": workflow_config.agent_type}
                
            # Get agent configs
            agents = {
                agent["name"]: agent
                for agent in kit_config.get("agents", [])
            }

            # Check workflow-specific agent
            agent_name = workflow_config.get("agent") 
            if not agent_name:
                # Check default agent at workflow root
                agent_name = kit_config.get("workflows", {}).get("agent")

            if not agent_name or agent_name not in agents:
                return None

            agent_config = agents[agent_name]
            return self.get_agent(
                kit_path=kit_path,
                agent_name=agent_name,
                class_name=agent_config["class"]
            )

        except Exception as e:
            raise AgentLoaderError(
                f"Failed to load workflow agent for {workflow_name}: {str(e)}"
            )
