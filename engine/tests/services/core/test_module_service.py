import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch
from engine.services.core.module import ModuleService, ModuleError, ModuleMetadata, RelationType

@pytest.fixture
def workspace_structure(temp_dir):
    """Create workspace directory structure"""
    owner = "test-owner"
    kit_id = "test-kit"
    version = "1.0.0"
    
    # Create workspace path
    workspace_path = temp_dir / owner / kit_id / version / "workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy file in workspace
    (workspace_path / "test.txt").write_text("test content")
    
    return {
        "owner": owner,
        "kit_id": kit_id,
        "version": version,
        "workspace_path": workspace_path
    }

@pytest.fixture
def module_service(temp_dir, mock_repo_service, mock_stage_state_service):
    return ModuleService(
        workspace_base=str(temp_dir),
        module_base=str(temp_dir),
        repo_service=mock_repo_service,
        stage_state_service=mock_stage_state_service
    )

def test_validate_path(module_service):
    # Test valid paths
    assert module_service._validate_path("abc.123")
    assert module_service._validate_path("service.auth.v1")
    assert module_service._validate_path("backend.users")

    # Test invalid paths
    assert not module_service._validate_path("abc..123")
    assert not module_service._validate_path(".abc.123")
    assert not module_service._validate_path("abc.123.")
    assert not module_service._validate_path("abc-123")


def test_get_linked_modules(module_service, mock_db_session):
    module_id = "test-module"
    
    mock_module = Mock()
    mock_mapping = Mock()
    mock_results = [(mock_module, mock_mapping)]
    
    with patch('engine.services.core.module.SessionLocal', return_value=mock_db_session):
        mock_db_session.execute.return_value.all.return_value = mock_results
        
        results = module_service.get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.CONNECTION
        )
        
        assert isinstance(results, list)
        assert len(results) == 1

# Add more test cases for error conditions
def test_create_module_invalid_path(module_service, workspace_structure):
    """Test creating module with invalid path"""
    with pytest.raises(ModuleError, match="Invalid path format"):
        module_service.create_module(
            project_id="test-project",
            owner=workspace_structure["owner"],
            kit_id=workspace_structure["kit_id"],
            version=workspace_structure["version"],
            env_vars={},
            path="invalid..path"
        )

def test_create_module_repo_error(module_service, mock_db_session, workspace_structure):
    """Test creating module with repository error"""
    # Setup
    module_service.repo_service.create_repository.side_effect = Exception("Repo error")
    
    with pytest.raises(ModuleError, match="Failed to create module: Repo error"):
        module_service.create_module(
            project_id="test-project",
            owner=workspace_structure["owner"],
            kit_id=workspace_structure["kit_id"],
            version=workspace_structure["version"],
            env_vars={},
            path="test.path"
        )