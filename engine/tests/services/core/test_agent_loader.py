"""Tests for AgentLoader service."""
import pytest
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock

from engine.services.core.agent_loader import AgentLoader, AgentLoaderError
from engine.services.agents.base_agent import (
    Action,
    AgentContext,
    AgentServices,
    BaseAgent
)

def test_load_workflow_agent_from_kit(tmp_path):
    """Should load workflow agent from kit config"""
    # Setup test kit
    kit_path = tmp_path / "test-kit"
    agents_dir = kit_path / "agents"
    agents_dir.mkdir(parents=True)
    
    # Create agent file
    with open(agents_dir / "mock.py", "w") as f:
        f.write("""
from engine.services.agents.base_agent import BaseAgent

class MockAgent(BaseAgent):
    @property
    def agent_type(self) -> str:
        return "mock"
    
    def _get_base_instructions(self) -> str:
        return "Mock agent instructions"

    @property
    def default_actions(self) -> List[Action]:
        return []

    async def _process_workflow(
        self,
        context: AgentContext,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {}
""")
    
    # Create kit.yaml
    with open(kit_path / "kit.yaml", "w") as f:
        f.write("""
docVersion: v1
id: test-kit
version: "0.1.0"

agents:
  - name: "mock"
    class: "MockAgent"
    description: "Mock agent for testing"

workflows:
  agent: "mock"
  
  test:
    agent: "mock"
    actions: []
""")

    # Create agent loader
    loader = AgentLoader(AgentServices(
        model_service=MagicMock(),
        workflow_service=MagicMock(),
        stage_state_service=MagicMock(),
        repo_service=MagicMock(),
        module_service=MagicMock()
    ))

    # Load workflow agent
    workflow_config = {"agent": "mock"}
    agent = loader.load_workflow_agent(
        kit_path,
        "test",
        workflow_config
    )

    # Verify agent
    assert agent is not None
    assert agent.agent_type == "mock"

def test_load_workflow_agent_from_base(tmp_path):
    """Should load workflow agent from base.agents if not in kit"""
    # Setup test kit
    kit_path = tmp_path / "test-kit"
    agents_dir = kit_path / "agents"
    agents_dir.mkdir(parents=True)

    # Create empty __init__.py
    (agents_dir / "__init__.py").touch()

    # Create kit.yaml
    with open(kit_path / "kit.yaml", "w") as f:
        f.write("""
docVersion: v1
id: test-kit
version: "0.1.0"

agents:
  - name: "tasker"
    class: "TaskerAgent"
    description: "Tasker agent for testing"

workflows:
  agent: "tasker"
  
  test:
    agent: "tasker"
    actions: []
""")

    # Create agent loader
    loader = AgentLoader(AgentServices(
        model_service=MagicMock(),
        workflow_service=MagicMock(),
        stage_state_service=MagicMock(),
        repo_service=MagicMock(),
        module_service=MagicMock()
    ))

    # Load workflow agent
    workflow_config = {"agent": "tasker"}
    agent = loader.load_workflow_agent(
        kit_path,
        "test",
        workflow_config
    )

    # Verify agent loaded from base.agents
    assert agent is not None
    assert agent.agent_type == "tasker"
