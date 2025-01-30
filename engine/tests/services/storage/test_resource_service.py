# tests/services/storage/test_resource_service.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from engine.services.storage.resource import ResourceService, Resource, ResourceError

@pytest.fixture
def mock_module_service():
    service = Mock()
    mock_metadata = Mock(repo_name="test-repo")
    service.get_module_metadata.return_value = mock_metadata
    return service

@pytest.fixture
def resource_service(temp_dir, mock_module_service):
    return ResourceService(
        workspace_base=temp_dir / "workspace",
        module_base=temp_dir / "modules",
        repo_base=temp_dir / "repos",
        module_service=mock_module_service
    )

def test_get_documentation_resources(resource_service, temp_dir):
    # Create module path and set mock to return it
    module_path = temp_dir / "modules" / "test-module"
    resource_service.module_service.get_module_path.return_value = module_path
    
    # Create the instruction directory and file
    instruction_path = module_path / "instructions"
    instruction_path.mkdir(parents=True)
    doc_file = instruction_path / "docs" / "readme.md"
    doc_file.parent.mkdir(parents=True)
    doc_file.write_text("# README")

    # Mock the kit.yaml content
    with patch('engine.utils.yaml.YAMLUtils.read_kit') as mock_read_kit:
        mock_read_kit.return_value = {
            "instructions": {
                "documentation": [
                    {
                        "path": "docs/readme.md",
                        "description": "README"
                    }
                ]
            }
        }
        
        # Get resources
        resources = resource_service.get_documentation_resources("test-module")
        
        # Verify results
        assert len(resources) == 1
        assert resources[0].name == "readme.md"
        assert resources[0].content == "# README"
        assert resources[0].path == "docs/readme.md"

def test_get_specification_resources(resource_service, temp_dir):
    # Create module path and set mock to return it
    module_path = temp_dir / "modules" / "test-module"
    resource_service.module_service.get_module_path.return_value = module_path
    
    # Create the instruction directory and file
    instruction_path = module_path / "instructions"
    instruction_path.mkdir(parents=True)
    spec_file = instruction_path / "specs" / "api.yaml"
    spec_file.parent.mkdir(parents=True)
    spec_file.write_text("openapi: 3.0.0")

    # Mock the kit.yaml content
    with patch('engine.utils.yaml.YAMLUtils.read_kit') as mock_read_kit:
        mock_read_kit.return_value = {
            "instructions": {
                "specification": [
                    {
                        "path": "specs/api.yaml",
                        "description": "API Spec"
                    }
                ]
            }
        }
        
        # Get resources
        resources = resource_service.get_specification_resources("test-module")
        
        # Verify results
        assert len(resources) == 1
        assert resources[0].name == "api.yaml"
        assert resources[0].content == "openapi: 3.0.0"
        assert resources[0].path == "specs/api.yaml"

# Rest of the tests remain the same...

def test_get_workspace_resources(resource_service, temp_dir):
    # Setup
    repo_path = temp_dir / "repos" / "test-repo"
    repo_path.mkdir(parents=True)
    test_file = repo_path / "test.txt"
    test_file.write_text("test content")
    
    with patch('engine.utils.yaml.YAMLUtils.read_kit') as mock_read_kit:
        mock_read_kit.return_value = {
            "workspace": {
                "files": [
                    {"path": "*.txt", "description": "Text files"}
                ]
            }
        }
        
        resources = resource_service.get_workspace_resources("test-module")
        
        assert len(resources) == 1
        assert resources[0].name == "test.txt"
        assert resources[0].content == "test content"

def test_module_error_handling(resource_service):
    # Configure mock to raise ModuleError
    resource_service.module_service.get_module_metadata.side_effect = ResourceError("Module error")
    
    with pytest.raises(ResourceError, match="Module error"):
        resource_service.get_workspace_resources("test-module")

def test_resource_not_found(resource_service, temp_dir):
    # Update mock_module_service to return the temp_dir path
    resource_service.module_service.get_module_path.return_value = temp_dir
    
    with patch('engine.utils.yaml.YAMLUtils.read_kit') as mock_read_kit:
        mock_read_kit.return_value = {}
        
        assert resource_service.get_workspace_resources("test-module") == []
        assert resource_service.get_documentation_resources("test-module") == []
        assert resource_service.get_specification_resources("test-module") == []

def test_read_file_error(resource_service):
    with pytest.raises(ResourceError, match="Failed to read file"):
        resource_service._read_file_content(Path("/nonexistent/file.txt"))