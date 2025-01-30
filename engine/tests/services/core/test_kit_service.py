# tests/services/core/test_kit_service.py
import io
import pytest
import yaml
from datetime import datetime, UTC
from pathlib import Path
from zipfile import ZipFile
from engine.services.core.kit import (
    KitService, KitMetadata, KitError, KitNotFoundError,
    VersionExistsError, InvalidVersionError, VersionSort
)

@pytest.fixture
def kit_service(temp_dir):
    return KitService(base_path=temp_dir)

@pytest.fixture
def sample_kit_structure():
    """Create a sample kit structure in memory"""
    kit_files = {
        'kit.yaml': {
            'name': 'test-kit',
            'owner': 'test-owner',
            'id': 'test-kit-id',
            'version': '1.0.0',
            'docVersion': 'v1',
            'environment': [{'name': 'TEST_ENV', 'value': 'test'}]
        },
        'instructions/readme.md': '# Test Kit\nThis is a test kit.',
        'instructions/docs/usage.md': '## Usage\nHow to use this kit.',
        'actions/main.py': 'print("Hello, World!")',
        'workspace/example.txt': 'Example content'
    }
    return kit_files

@pytest.fixture
def kit_zip_file(sample_kit_structure):
    """Create a ZIP file with the kit structure"""
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for file_path, content in sample_kit_structure.items():
            if isinstance(content, dict):
                content = yaml.dump(content)
            zip_file.writestr(file_path, content)
    zip_buffer.seek(0)
    return zip_buffer

class TestKitService:
    def test_validate_semantic_version(self, kit_service):
        """Test version validation"""
        assert kit_service.validate_semantic_version("1.0.0")
        assert not kit_service.validate_semantic_version("1.0")
        assert not kit_service.validate_semantic_version("v1.0.0")

    def test_save_kit(self, kit_service, kit_zip_file, sample_kit_structure):
        """Test saving a new kit"""
        metadata = kit_service.save_kit(kit_zip_file)
        
        assert isinstance(metadata, KitMetadata)
        assert metadata.name == sample_kit_structure['kit.yaml']['name']
        assert metadata.version == sample_kit_structure['kit.yaml']['version']
        assert metadata.owner == sample_kit_structure['kit.yaml']['owner']
        
        # Verify directory structure
        kit_path = kit_service._get_kit_path(metadata.owner, metadata.kit_id, metadata.version)
        assert kit_path.exists()
        assert (kit_path / "kit.yaml").exists()
        assert (kit_path / "instructions").exists()
        assert (kit_path / "actions").exists()
        assert (kit_path / "workspace").exists()

    def test_save_kit_version_exists(self, kit_service, kit_zip_file):
        """Test saving a kit version that already exists"""
        kit_service.save_kit(kit_zip_file)
        kit_zip_file.seek(0)
        
        with pytest.raises(VersionExistsError):
            kit_service.save_kit(kit_zip_file)

    def test_get_kit_versions(self, kit_service, kit_zip_file, sample_kit_structure):
        """Test getting kit versions"""
        # Save initial version
        kit_service.save_kit(kit_zip_file)
        
        # Create and save another version
        kit_data = sample_kit_structure['kit.yaml'].copy()
        kit_data['version'] = '2.0.0'
        
        new_zip = io.BytesIO()
        with ZipFile(new_zip, 'w') as zip_file:
            zip_file.writestr('kit.yaml', yaml.dump(kit_data))
        new_zip.seek(0)
        
        kit_service.save_kit(new_zip)
        
        # Test version listing
        versions = kit_service.get_kit_versions(
            owner=kit_data['owner'],
            kit_id=kit_data['id']
        )
        assert len(versions) == 2
        assert versions == ['1.0.0', '2.0.0']  # Ascending order by default

    def test_delete_kit_version(self, kit_service, kit_zip_file, sample_kit_structure):
        """Test deleting a specific kit version"""
        metadata = kit_service.save_kit(kit_zip_file)
        
        kit_service.delete_kit_version(
            owner=metadata.owner,
            kit_id=metadata.kit_id,
            version=metadata.version
        )
        
        kit_path = kit_service._get_kit_path(metadata.owner, metadata.kit_id, metadata.version)
        assert not kit_path.exists()

    def test_delete_kit(self, kit_service, kit_zip_file):
        """Test deleting entire kit"""
        metadata = kit_service.save_kit(kit_zip_file)
        
        kit_service.delete_kit(
            owner=metadata.owner,
            kit_id=metadata.kit_id
        )
        
        kit_path = kit_service._get_kit_path(metadata.owner, metadata.kit_id)
        assert not kit_path.exists()

    def test_get_all_kits(self, kit_service, kit_zip_file, sample_kit_structure):
        """Test getting all kits"""
        # Save initial version
        kit_service.save_kit(kit_zip_file)
        
        # Create and save another kit
        kit_data = sample_kit_structure['kit.yaml'].copy()
        kit_data['id'] = 'another-kit'
        kit_data['name'] = 'Another Kit'
        
        new_zip = io.BytesIO()
        with ZipFile(new_zip, 'w') as zip_file:
            zip_file.writestr('kit.yaml', yaml.dump(kit_data))
        new_zip.seek(0)
        
        kit_service.save_kit(new_zip)
        
        # Get all kits
        kits = kit_service.get_all_kits()
        assert len(kits) == 2
        assert sorted([k.name for k in kits]) == ['Another Kit', 'test-kit']

    def test_invalid_kit_yaml(self, kit_service):
        """Test handling invalid kit.yaml"""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('kit.yaml', 'invalid: yaml: content')
        zip_buffer.seek(0)
        
        with pytest.raises(KitError, match="Invalid kit.yaml"):
            kit_service.save_kit(zip_buffer)

    def test_missing_required_fields(self, kit_service):
        """Test handling missing required fields"""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('kit.yaml', yaml.dump({'name': 'test'}))
        zip_buffer.seek(0)
        
        with pytest.raises(KitError, match="Missing required fields"):
            kit_service.save_kit(zip_buffer)