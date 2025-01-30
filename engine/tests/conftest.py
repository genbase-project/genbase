import pytest
from pathlib import Path
from unittest.mock import Mock

# Enable PDM pytest plugins
pytest_plugins = ["pdm.pytest"]

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture
def mock_db_session():
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    return session

@pytest.fixture
def mock_repo_service():
    return Mock()

@pytest.fixture
def mock_stage_state_service():
    return Mock()

# Add project-specific fixtures using PDM's project fixture
@pytest.fixture
def engine_project(project):
    """Initialize a PDM project with our engine package"""
    project.pyproject.settings["project"] = {
        "name": "engine",
        "version": "0.1.0",
        "dependencies": [],
    }
    return project