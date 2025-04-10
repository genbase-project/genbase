"""Agent plugin loader service."""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Type, Optional, Union

from engine.services.agents.base_agent import BaseAgent, AgentServices
from engine.services.execution.profile_config import ProfileConfig
from loguru import logger
from engine.base.agents import __all__ as base_agents

class AgentLoaderError(Exception):
    """Base exception for agent loading errors"""
    pass

class AgentLoader:
    """Dynamically loads agent plugins from kits"""
    
    def __init__(self, agent_services: AgentServices):
        self.agent_services = agent_services
        self.loaded_agents: Dict[str, Type[BaseAgent]] = {}
        self._load_base_agents()

    def _load_base_agents(self):
        """Load built-in agents from base.agents"""
        try:
            from engine.base.agents import __all__ as agent_classes
            for agent_class in agent_classes:
                # Create instance to get agent_type
                agent = agent_class(self.agent_services)
                self.loaded_agents[agent.agent_type] = agent_class
        except Exception as e:
            logger.error(f"Failed to load base agents: {str(e)}")
            raise AgentLoaderError(f"Failed to load base agents: {str(e)}")

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
            # Check if it's a base agent first
            if agent_name in self.loaded_agents:
                agent_class = self.loaded_agents[agent_name]
                return agent_class(self.agent_services)

            # Load from kit
            agents_dir = kit_path / "agents"
            if not agents_dir.exists():
                raise AgentLoaderError(f"Agents directory not found: {agents_dir}")

            # Create cache key 
            cache_key = f"{kit_path}:{agent_name}"

            # Return cached agent class if available
            if cache_key in self.loaded_agents:
                agent_class = self.loaded_agents[cache_key]
                return agent_class(self.agent_services)

            # Import agent module from kit
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

            # Get agent class
            if not hasattr(module, class_name):
                raise AgentLoaderError(f"Agent class {class_name} not found in {module_path}")

            agent_class = getattr(module, class_name)
            if not issubclass(agent_class, BaseAgent):
                raise AgentLoaderError(f"{class_name} in {module_path} is not a BaseAgent subclass")
                
            # Create instance to get agent_type value
            agent_instance = agent_class(self.agent_services)
            if agent_instance.agent_type != agent_name:
                raise AgentLoaderError(f"Agent type mismatch: class {class_name} has agent_type '{agent_instance.agent_type}' but kit.yaml specifies '{agent_name}'")

            # Cache agent class
            self.loaded_agents[cache_key] = agent_class
            return agent_instance

        except Exception as e:
            raise AgentLoaderError(f"Failed to get agent {agent_name}: {str(e)}")

    def load_profile_agent(
        self,
        kit_path: Path,
        profile_name: str,
        profile_config: Union[dict, ProfileConfig]
    ) -> Optional[BaseAgent]:
        """
        Load agent for specific profile based on kit.yaml config.

        Args:
            kit_path: Path to kit root directory
            profile_name: Name of profile
            profile_config: profile configuration from kit.yaml

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

            # Convert profileConfig to dict if needed
            if isinstance(profile_config, ProfileConfig):
                profile_config = {"agent": profile_config.agent_type}
                
            # Get agent configs
            agents = {
                agent["name"]: agent
                for agent in kit_config.get("agents", [])
            }

            # Check profile-specific agent
            agent_name = profile_config.get("agent") 
            if not agent_name:
                # Check default agent at profile root
                agent_name = kit_config.get("profiles", {}).get("agent")

            if not agent_name:
                raise AgentLoaderError(f"No agent specified for profile {profile_name}")
                
            # First try loading from base agents
            if agent_name in self.loaded_agents:
                return self.get_agent(kit_path, agent_name, agent_name)
                
            # Load from kit if not a base agent
            if agent_name not in agents:
                raise AgentLoaderError(f"Agent '{agent_name}' not found in kit.yaml agents")

            agent_config = agents[agent_name]
            return self.get_agent(
                kit_path=kit_path,
                agent_name=agent_name,
                class_name=agent_config["class"]
            )

        except Exception as e:
            raise AgentLoaderError(
                f"Failed to load profile agent for {profile_name}: {str(e)}"
            )
