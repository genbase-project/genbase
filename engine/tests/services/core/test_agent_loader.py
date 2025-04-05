import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from engine.services.agents.base_agent import BaseAgent, AgentServices
from engine.services.core.agent_loader import AgentLoader, AgentLoaderError
from engine.services.execution.profile_config import ProfileConfig
from engine.base.agents import TaskerAgent # Import a known base agent


# --- Fixtures ---

@pytest.fixture
def mock_agent_services() -> MagicMock:
    """Mock AgentServices dependency."""
    services = MagicMock(spec=AgentServices)
    return services

@pytest.fixture
def agent_loader(mock_agent_services: MagicMock) -> AgentLoader:
    """Fixture providing an AgentLoader instance."""
    return AgentLoader(agent_services=mock_agent_services)

@pytest.fixture
def tmp_kit_path(tmp_path: Path) -> Path:
    """Create a temporary directory representing a kit."""
    kit_dir = tmp_path / "test_kit_dir"
    kit_dir.mkdir()
    return kit_dir

@pytest.fixture
def create_dummy_agent_file(tmp_kit_path: Path):
    """Factory fixture to create a dummy agent file within the kit path."""
    def _create_file(
        agent_name: str,
        class_name: str,
        content: str = None,
        is_init_py: bool = False
    ):
        agents_dir = tmp_kit_path / "agents"
        agents_dir.mkdir(exist_ok=True)
        file_name = "__init__.py" if is_init_py else f"{agent_name}.py"
        agent_file = agents_dir / file_name

        if content is None:
            # Basic valid agent structure
            content = f"""
from engine.services.agents.base_agent import BaseAgent, AgentContext

class {class_name}(BaseAgent):
    @property
    def agent_type(self) -> str:
        return "{agent_name}"

    async def process_request(self, context: AgentContext, profile_data: dict):
        return {{"response": "dummy response from {agent_name}"}}
"""
        agent_file.write_text(content)
        return agent_file
    return _create_file

@pytest.fixture
def create_kit_yaml(tmp_kit_path: Path):
    """Factory fixture to create a kit.yaml file."""
    def _create_yaml(config: dict):
        kit_yaml_path = tmp_kit_path / "kit.yaml"
        with open(kit_yaml_path, 'w') as f:
            yaml.dump(config, f)
        return kit_yaml_path
    return _create_yaml

# --- Test Cases ---

class TestAgentLoader:

    def test_init_loads_base_agents(self, agent_loader: AgentLoader):
        """Test that base agents are loaded during initialization."""
        assert "tasker" in agent_loader.loaded_agents
        assert agent_loader.loaded_agents["tasker"] == TaskerAgent

    def test_get_agent_load_base_agent(self, agent_loader: AgentLoader, tmp_kit_path: Path):
        """Test getting a known base agent instance."""
        agent = agent_loader.get_agent(tmp_kit_path, "tasker", "TaskerAgent")
        assert isinstance(agent, TaskerAgent)
        assert agent.agent_type == "tasker"

    def test_get_agent_load_custom_agent_success(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test loading a custom agent from a kit file."""
        agent_name = "custom_agent"
        class_name = "CustomAgentClass"
        create_dummy_agent_file(agent_name, class_name)

        # Ensure it's not loaded yet (beyond base agents)
        assert f"{tmp_kit_path}:{agent_name}" not in agent_loader.loaded_agents

        agent = agent_loader.get_agent(tmp_kit_path, agent_name, class_name)

        assert isinstance(agent, BaseAgent)
        assert not isinstance(agent, TaskerAgent) # Ensure it's not the base one
        assert agent.agent_type == agent_name
        # Check if it's cached now
        assert f"{tmp_kit_path}:{agent_name}" in agent_loader.loaded_agents

    def test_get_agent_load_custom_agent_from_init(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test loading a custom agent from agents/__init__.py."""
        agent_name = "init_agent"
        class_name = "InitAgentClass"
        # Create agent in __init__.py instead of init_agent.py
        create_dummy_agent_file(agent_name, class_name, is_init_py=True)

        agent = agent_loader.get_agent(tmp_kit_path, agent_name, class_name)

        assert isinstance(agent, BaseAgent)
        assert agent.agent_type == agent_name

    def test_get_agent_load_cached_custom_agent(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test that loading the same custom agent again uses the cache."""
        agent_name = "cache_test_agent"
        class_name = "CacheTestAgentClass"
        agent_file_path = create_dummy_agent_file(agent_name, class_name)

        # Load first time to cache it
        agent1 = agent_loader.get_agent(tmp_kit_path, agent_name, class_name)
        assert f"{tmp_kit_path}:{agent_name}" in agent_loader.loaded_agents

        # Modify the file content - if cache works, this won't be loaded
        agent_file_path.write_text("INVALID PYTHON SYNTAX {")

        # Load second time
        agent2 = agent_loader.get_agent(tmp_kit_path, agent_name, class_name)

        assert agent1 is not agent2 # Should be different instances
        assert type(agent1) is type(agent2) # But the same class from cache
        assert agent2.agent_type == agent_name # Verify it's the correct agent

    def test_get_agent_agents_dir_not_found(self, agent_loader: AgentLoader, tmp_kit_path: Path):
        """Test error when agents directory is missing."""
        with pytest.raises(AgentLoaderError, match="Agents directory not found"):
            agent_loader.get_agent(tmp_kit_path, "some_agent", "SomeClass")

    def test_get_agent_module_file_not_found(self, agent_loader: AgentLoader, tmp_kit_path: Path):
        """Test error when specific agent .py or __init__.py is missing."""
        agents_dir = tmp_kit_path / "agents"
        agents_dir.mkdir() # Create agents dir, but no files inside
        with pytest.raises(AgentLoaderError, match="No agent module found"):
            agent_loader.get_agent(tmp_kit_path, "missing_agent", "MissingClass")

    def test_get_agent_class_not_found(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test error when the specified class is not in the loaded module."""
        agent_name = "class_not_found_agent"
        correct_class_name = "CorrectClass"
        wrong_class_name = "WrongClass"
        create_dummy_agent_file(agent_name, correct_class_name)

        with pytest.raises(AgentLoaderError, match=f"Agent class {wrong_class_name} not found"):
            agent_loader.get_agent(tmp_kit_path, agent_name, wrong_class_name)

    def test_get_agent_not_base_agent_subclass(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test error when loaded class does not inherit from BaseAgent."""
        agent_name = "not_subclass_agent"
        class_name = "NotASubclass"
        # Create a file with a class that doesn't inherit BaseAgent
        content = f"class {class_name}:\n    pass\n"
        create_dummy_agent_file(agent_name, class_name, content=content)

        with pytest.raises(AgentLoaderError, match=f"{class_name} .* is not a BaseAgent subclass"):
            agent_loader.get_agent(tmp_kit_path, agent_name, class_name)

    def test_get_agent_type_mismatch(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file):
        """Test error when agent_type property doesn't match requested agent_name."""
        requested_agent_name = "requested_name"
        actual_agent_type = "actual_type" # The type defined inside the class
        class_name = "TypeMismatchAgent"
        # Create file where agent_type != requested_agent_name
        content = f"""
from engine.services.agents.base_agent import BaseAgent, AgentContext

class {class_name}(BaseAgent):
    @property
    def agent_type(self) -> str:
        return "{actual_agent_type}" # Different from requested_agent_name

    async def process_request(self, context: AgentContext, profile_data: dict):
        return {{"response": "dummy"}}
"""
        create_dummy_agent_file(requested_agent_name, class_name, content=content)

        with pytest.raises(AgentLoaderError, match=f"Agent type mismatch: class {class_name} has agent_type '{actual_agent_type}' but kit.yaml specifies '{requested_agent_name}'"):
            agent_loader.get_agent(tmp_kit_path, requested_agent_name, class_name)

    def test_load_profile_agent_success_profile_specific(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file, create_kit_yaml):
        """Test loading agent specified in a specific profile config."""
        agent_name = "profile_agent"
        class_name = "ProfileAgentClass"
        create_dummy_agent_file(agent_name, class_name)
        kit_config = {
            "agents": [{"name": agent_name, "class": class_name}],
            "profiles": {
                "my_profile": {"agent": agent_name}
            }
        }
        create_kit_yaml(kit_config)
        profile_config = kit_config["profiles"]["my_profile"] # Use dict config

        agent = agent_loader.load_profile_agent(tmp_kit_path, "my_profile", profile_config)
        assert isinstance(agent, BaseAgent)
        assert agent.agent_type == agent_name

    def test_load_profile_agent_success_default_agent(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file, create_kit_yaml):
        """Test loading agent using default agent specified at profiles root."""
        agent_name = "default_kit_agent"
        class_name = "DefaultKitAgentClass"
        create_dummy_agent_file(agent_name, class_name)
        kit_config = {
            "agents": [{"name": agent_name, "class": class_name}],
            "profiles": {
                "agent": agent_name, # Default agent here
                "my_profile": {} # No agent specified for this profile
            }
        }
        create_kit_yaml(kit_config)
        profile_config = kit_config["profiles"]["my_profile"]

        agent = agent_loader.load_profile_agent(tmp_kit_path, "my_profile", profile_config)
        assert isinstance(agent, BaseAgent)
        assert agent.agent_type == agent_name

    def test_load_profile_agent_base_agent(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_kit_yaml):
        """Test loading a base agent specified in profile config."""
        kit_config = {
             "agents": [], # No custom agents defined
             "profiles": {
                 "tasker_profile": {"agent": "tasker"}
             }
        }
        create_kit_yaml(kit_config)
        profile_config = kit_config["profiles"]["tasker_profile"]

        agent = agent_loader.load_profile_agent(tmp_kit_path, "tasker_profile", profile_config)
        assert isinstance(agent, TaskerAgent) # Check it's the base TaskerAgent
        assert agent.agent_type == "tasker"

    def test_load_profile_agent_using_profile_config_object(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_dummy_agent_file, create_kit_yaml):
        """Test loading agent using ProfileConfig object."""
        agent_name = "config_obj_agent"
        class_name = "ConfigObjAgentClass"
        create_dummy_agent_file(agent_name, class_name)
        kit_config = {
            "agents": [{"name": agent_name, "class": class_name}],
            "profiles": {
                "my_profile": {"agent": agent_name} # Agent defined in kit.yaml
            }
        }
        create_kit_yaml(kit_config)
        # Create ProfileConfig object referencing the agent
        profile_config_obj = ProfileConfig(profile_type="my_profile", agent_type=agent_name)

        agent = agent_loader.load_profile_agent(tmp_kit_path, "my_profile", profile_config_obj)
        assert isinstance(agent, BaseAgent)
        assert agent.agent_type == agent_name

    def test_load_profile_agent_no_agent_specified(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_kit_yaml):
        """Test error when no agent is specified in profile or defaults."""
        kit_config = {
            "agents": [],
            "profiles": {
                "no_agent_profile": {} # No agent here or at root
            }
        }
        create_kit_yaml(kit_config)
        profile_config = kit_config["profiles"]["no_agent_profile"]

        with pytest.raises(AgentLoaderError, match="No agent specified for profile"):
            agent_loader.load_profile_agent(tmp_kit_path, "no_agent_profile", profile_config)

    def test_load_profile_agent_name_not_in_kit_agents(self, agent_loader: AgentLoader, tmp_kit_path: Path, create_kit_yaml):
        """Test error when specified agent is not defined in kit.yaml agents section."""
        kit_config = {
            "agents": [], # Agent 'missing_agent_def' is not listed here
            "profiles": {
                "bad_agent_profile": {"agent": "missing_agent_def"}
            }
        }
        create_kit_yaml(kit_config)
        profile_config = kit_config["profiles"]["bad_agent_profile"]

        with pytest.raises(AgentLoaderError, match="Agent 'missing_agent_def' not found in kit.yaml agents"):
            agent_loader.load_profile_agent(tmp_kit_path, "bad_agent_profile", profile_config)

    def test_load_profile_agent_kit_yaml_not_found(self, agent_loader: AgentLoader, tmp_kit_path: Path):
        """Test error when kit.yaml is missing."""
        # Don't call create_kit_yaml
        profile_config = {"agent": "any_agent"}
        with pytest.raises(AgentLoaderError, match="Failed to load profile agent"): # Outer exception wraps inner FileNotFoundError
            agent_loader.load_profile_agent(tmp_kit_path, "some_profile", profile_config)

    # Cleanup dynamically loaded modules after tests run
    @classmethod
    def teardown_class(cls):
        modules_to_remove = [
            name for name in sys.modules if name.startswith("dynamic_agents_")
        ]
        for name in modules_to_remove:
            del sys.modules[name]