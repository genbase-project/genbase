# tests/services/core/test_kit.py

import pytest
import io
import os
import tarfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
from httpx import Response, Request

from engine.services.core.kit import (
    KitService,
    KitError,
    KitNotFoundError,
    VersionExistsError,
    InvalidVersionError,
    RegistryError,
    KitMetadata,
    KitConfig,
    VersionSort,
    ProfileAction,
    InstructionItem
)

KIT_OWNER = "test_owner"
KIT_ID = "test-kit"
VALID_VERSION = "1.0.0"
VALID_VERSION_2 = "1.1.0"
INVALID_VERSION = "1.0"
REGISTRY_URL = "http://fake-registry.com"

# --- Fixtures ---

@pytest.fixture
def kit_service(tmp_path: Path) -> KitService:
    base_path = tmp_path / "kits"
    base_path.mkdir()
    return KitService(base_path=base_path)

@pytest.fixture
def sample_kit_config_dict() -> dict:
    return {
        "docVersion": "v1",
        "id": KIT_ID,
        "version": VALID_VERSION,
        "name": "Test Kit Name",
        "owner": KIT_OWNER,
        "environment": [{"name": "API_KEY", "description": "Test API Key", "required": True}],
        "agents": [{"name": "test_agent", "class": "TestAgent"}],
        "profiles": {
            "initialize": {
                "agent": "test_agent",
                "actions": [
                    {"path": "init_action", "name": "Initialize Action", "description": "Runs init"},
                    {"path": "another:setup_action", "name": "Setup Action"}
                ],
                "instructions": [
                    {"path": "init_guide.md", "name": "Initialization Guide"}
                ]
            }
        },
        "provide": {
            "actions": [{"path": "provided_func", "name": "Shared Utility"}],
            "instructions": [{"path": "shared_docs.md", "name": "Shared Documentation"}],
            "workspace": {"description": "Shared workspace files"}
        },
        "dependencies": ["requests"],
        "workspace": {
            "files": [{"path": "config/default.json", "description": "Default config"}],
            "ignore": [".env", "*.log"]
        },
        "image": "custom-python:3.12",
        "ports": [{"port": 8080, "name": "web"}]
    }

def create_kit_archive(tmp_path: Path, config: dict, archive_name: str, include_top_dir=True, add_files=True) -> io.BytesIO:
    archive_path = tmp_path / archive_name
    kit_root_name = archive_name.replace('.tar.gz', '') if include_top_dir else ""
    kit_content_path = tmp_path / "kit_content" / kit_root_name
    kit_content_path.mkdir(parents=True, exist_ok=True)

    kit_yaml_path = kit_content_path / "kit.yaml"
    with open(kit_yaml_path, 'w') as f:
        yaml.dump(config, f)

    if add_files:
        actions_dir = kit_content_path / "actions"
        actions_dir.mkdir(exist_ok=True)
        (actions_dir / "__init__.py").write_text("def init_action(): pass\ndef provided_func(): pass")
        (actions_dir / "another.py").write_text("def setup_action(): pass")

        instructions_dir = kit_content_path / "instructions"
        instructions_dir.mkdir(exist_ok=True)
        (instructions_dir / "init_guide.md").write_text("# Init Guide")
        (instructions_dir / "shared_docs.md").write_text("# Shared Docs")

        config_dir = kit_content_path / "config"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "default.json").write_text('{"key": "value"}')

    with tarfile.open(archive_path, "w:gz") as tar:
        source_dir = tmp_path / "kit_content"
        # Use arcname='.' to add contents directly if no top dir
        arc_base_name = kit_root_name if include_top_dir else '.'
        tar.add(str(kit_content_path), arcname=arc_base_name, recursive=True)

    archive_io = io.BytesIO(archive_path.read_bytes())
    shutil.rmtree(tmp_path / "kit_content")
    archive_path.unlink()
    return archive_io

@pytest.fixture
def sample_kit_archive(tmp_path: Path, sample_kit_config_dict: dict) -> io.BytesIO:
    archive_name = f"{sample_kit_config_dict['owner']}-{sample_kit_config_dict['id']}-{sample_kit_config_dict['version']}.tar.gz"
    return create_kit_archive(tmp_path, sample_kit_config_dict, archive_name)

@pytest.fixture
def create_saved_kit(kit_service: KitService, sample_kit_archive: io.BytesIO) -> KitMetadata:
    # Make sure the stream is at the beginning
    sample_kit_archive.seek(0)
    return kit_service.save_kit(sample_kit_archive)

@pytest.fixture(autouse=True)
def mock_registry_env():
    with patch.dict(os.environ, {"REGISTRY_URL": REGISTRY_URL}):
        yield

@pytest.fixture
def mock_httpx_client():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    return mock_client

def create_mock_response(status_code: int, json_data: dict = None, content: bytes = None, request_url: str = "http://test.com") -> Response:
    """Helper to create mock httpx.Response with a request object."""
    request = Request(method="GET", url=request_url)
    response = Response(status_code=status_code, json=json_data, content=content, request=request)
    # Manually set _request because the constructor doesn't always do it as expected with mocks
    response._request = request
    return response


# --- Test Cases ---

class TestKitService:

    def test_init_creates_base_path(self, tmp_path: Path):
        base_path = tmp_path / "new_kits"
        assert not base_path.exists()
        KitService(base_path=base_path)
        assert base_path.exists()

    def test_validate_semantic_version(self, kit_service: KitService):
        assert kit_service.validate_semantic_version("1.0.0") is True
        assert kit_service.validate_semantic_version("0.1.2") is True
        assert kit_service.validate_semantic_version("10.20.30") is True
        assert kit_service.validate_semantic_version("1.0") is False
        assert kit_service.validate_semantic_version("1") is False
        assert kit_service.validate_semantic_version("1.0.0-beta") is False
        assert kit_service.validate_semantic_version("v1.0.0") is False
        assert kit_service.validate_semantic_version("invalid") is False

    def test_get_kit_path(self, kit_service: KitService):
        assert kit_service.get_kit_path("owner", "id") == kit_service.base_path / "owner" / "id"
        assert kit_service.get_kit_path("owner", "id", "1.0.0") == kit_service.base_path / "owner" / "id" / "1.0.0"

    def test_save_kit_success(self, kit_service: KitService, sample_kit_archive: io.BytesIO, sample_kit_config_dict: dict):
        metadata = kit_service.save_kit(sample_kit_archive)

        assert isinstance(metadata, KitMetadata)
        assert metadata.owner == KIT_OWNER
        assert metadata.kit_id == KIT_ID
        assert metadata.version == VALID_VERSION
        assert metadata.name == sample_kit_config_dict["name"]

        kit_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert kit_path.exists()
        assert (kit_path / "kit.yaml").exists()
        assert (kit_path / "actions" / "__init__.py").exists()
        assert (kit_path / "instructions" / "init_guide.md").exists()
        assert (kit_path / "config" / "default.json").exists()

    def test_save_kit_no_top_level_dir(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        archive_name = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_io = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name, include_top_dir=False)
        metadata = kit_service.save_kit(archive_io)

        assert isinstance(metadata, KitMetadata)
        assert metadata.owner == KIT_OWNER
        assert metadata.version == VALID_VERSION

        kit_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert kit_path.exists()
        assert (kit_path / "kit.yaml").exists()
        assert (kit_path / "actions" / "__init__.py").exists() # Check a nested file

    def test_save_kit_missing_yaml(self, kit_service: KitService, tmp_path: Path):
        archive_name = "bad.tar.gz"
        archive_path = tmp_path / archive_name
        kit_content_path = tmp_path / "kit_content" / archive_name.replace('.tar.gz', '')
        kit_content_path.mkdir(parents=True)
        (kit_content_path / "dummy.txt").touch()

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(str(kit_content_path), arcname=archive_name.replace('.tar.gz', ''), recursive=True)

        with pytest.raises(KitError, match="kit.yaml not found"):
            kit_service.save_kit(io.BytesIO(archive_path.read_bytes()))

    def test_save_kit_invalid_yaml_format(self, kit_service: KitService, tmp_path: Path):
        archive_name = "bad.tar.gz"
        archive_path = tmp_path / archive_name
        kit_content_path = tmp_path / "kit_content" / archive_name.replace('.tar.gz', '')
        kit_content_path.mkdir(parents=True)
        (kit_content_path / "kit.yaml").write_text("id: test\nversion: [invalid")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(str(kit_content_path), arcname=archive_name.replace('.tar.gz', ''), recursive=True)

        with pytest.raises(KitError, match="Invalid kit.yaml"):
             kit_service.save_kit(io.BytesIO(archive_path.read_bytes()))

    def test_save_kit_missing_required_fields(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        config = sample_kit_config_dict.copy()
        archive_name = f"{config['owner']}-{config['id']}-invalid.tar.gz" # Use valid parts for name
        del config["version"] # Remove a required field after getting name parts
        archive_io = create_kit_archive(tmp_path, config, archive_name)
        with pytest.raises(KitError, match="Missing required fields"):
            kit_service.save_kit(archive_io)

    def test_save_kit_invalid_version_format(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        config = sample_kit_config_dict.copy()
        config["version"] = INVALID_VERSION
        archive_name = f"{config['owner']}-{config['id']}-{config['version']}.tar.gz"
        archive_io = create_kit_archive(tmp_path, config, archive_name)
        with pytest.raises(InvalidVersionError, match="Invalid version format"):
            kit_service.save_kit(archive_io)

    def test_save_kit_version_exists_no_overwrite(self, kit_service: KitService, create_saved_kit, tmp_path: Path, sample_kit_config_dict: dict):
         # Recreate the archive stream as the previous one was consumed
        archive_name = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_io = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name)
        with pytest.raises(VersionExistsError):
            kit_service.save_kit(archive_io, allow_overwrite=False)

    def test_save_kit_version_exists_with_overwrite(self, kit_service: KitService, create_saved_kit, tmp_path: Path, sample_kit_config_dict: dict):
        config = sample_kit_config_dict.copy()
        config["name"] = "Overwritten Name"
        archive_name = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        overwrite_archive_io = create_kit_archive(tmp_path, config, archive_name)

        metadata = kit_service.save_kit(overwrite_archive_io, allow_overwrite=True)
        assert metadata.name == "Overwritten Name"
        kit_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert kit_path.exists()

    def test_get_all_kits_empty(self, kit_service: KitService):
        assert kit_service.get_all_kits() == []

    def test_get_all_kits_single(self, kit_service: KitService, create_saved_kit: KitMetadata):
        kits = kit_service.get_all_kits()
        assert len(kits) == 1
        assert kits[0].owner == KIT_OWNER
        assert kits[0].kit_id == KIT_ID
        assert kits[0].version == VALID_VERSION

    def test_get_all_kits_multiple_versions(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        archive_name_v1 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_v1 = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name_v1)
        kit_service.save_kit(archive_v1)

        config_v2 = sample_kit_config_dict.copy()
        config_v2["version"] = VALID_VERSION_2
        archive_name_v2 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION_2}.tar.gz"
        archive_v2 = create_kit_archive(tmp_path, config_v2, archive_name_v2)
        kit_service.save_kit(archive_v2)

        kits = kit_service.get_all_kits(sort_by_name=True)
        assert len(kits) == 2
        assert kits[0].version == VALID_VERSION
        assert kits[1].version == VALID_VERSION_2

    def test_get_kit_versions_success(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        archive_name_v1 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_v1 = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name_v1)
        kit_service.save_kit(archive_v1)
        config_v2 = sample_kit_config_dict.copy(); config_v2["version"] = VALID_VERSION_2
        archive_name_v2 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION_2}.tar.gz"
        archive_v2 = create_kit_archive(tmp_path, config_v2, archive_name_v2)
        kit_service.save_kit(archive_v2)

        versions_asc = kit_service.get_kit_versions(KIT_OWNER, KIT_ID, sort=VersionSort.ASCENDING)
        assert versions_asc == [VALID_VERSION, VALID_VERSION_2]

        versions_desc = kit_service.get_kit_versions(KIT_OWNER, KIT_ID, sort=VersionSort.DESCENDING)
        assert versions_desc == [VALID_VERSION_2, VALID_VERSION]

    def test_get_kit_versions_not_found(self, kit_service: KitService):
        with pytest.raises(KitNotFoundError):
            kit_service.get_kit_versions("non_owner", "non_id")

    def test_get_kit_content_path_success(self, kit_service: KitService, create_saved_kit: KitMetadata):
        path = kit_service.get_kit_content_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        expected_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert path == expected_path
        assert path.exists()

    def test_get_kit_content_path_not_found(self, kit_service: KitService):
        with pytest.raises(KitNotFoundError):
            kit_service.get_kit_content_path(KIT_OWNER, KIT_ID, VALID_VERSION)

    def test_get_kit_content_path_invalid_version(self, kit_service: KitService, create_saved_kit: KitMetadata):
        with pytest.raises(InvalidVersionError):
            kit_service.get_kit_content_path(KIT_OWNER, KIT_ID, INVALID_VERSION)

    def test_get_kit_config_success(self, kit_service: KitService, create_saved_kit: KitMetadata, sample_kit_config_dict: dict):
        config = kit_service.get_kit_config(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert isinstance(config, KitConfig)
        assert config.owner == KIT_OWNER
        assert config.id == KIT_ID
        assert config.version == VALID_VERSION
        assert config.name == sample_kit_config_dict["name"]
        assert len(config.profiles) == 1
        assert "initialize" in config.profiles
        init_profile = config.profiles["initialize"]
        assert init_profile.agent == "test_agent"
        assert len(init_profile.actions) == 2
        assert isinstance(init_profile.actions[0], ProfileAction)
        assert init_profile.actions[0].name == "Initialize Action"
        assert init_profile.actions[0].function_name == "init_action"
        assert init_profile.actions[0].full_file_path.endswith("actions/__init__.py")
        assert init_profile.actions[1].name == "Setup Action"
        assert init_profile.actions[1].function_name == "setup_action"
        assert init_profile.actions[1].full_file_path.endswith("actions/another.py")
        assert len(init_profile.instructions) == 1
        assert isinstance(init_profile.instructions[0], InstructionItem)
        assert init_profile.instructions[0].name == "Initialization Guide"
        assert init_profile.instructions[0].content == "# Init Guide"

        assert len(config.provide.actions) == 1
        assert config.provide.actions[0].name == "Shared Utility"
        assert config.profiles["initialize"].actions[0].full_file_path.startswith(str(kit_service.base_path))




    def test_delete_kit_version_success(self, kit_service: KitService, create_saved_kit: KitMetadata):
        kit_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert kit_path.exists()
        kit_service.delete_kit_version(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert not kit_path.exists()
        assert not kit_service.get_kit_path(KIT_OWNER, KIT_ID).exists()
        assert not kit_service.get_kit_path(KIT_OWNER, "").exists()

    def test_delete_kit_version_multiple_exist(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        archive_name_v1 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_v1 = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name_v1)
        kit_service.save_kit(archive_v1)
        config_v2 = sample_kit_config_dict.copy(); config_v2["version"] = VALID_VERSION_2
        archive_name_v2 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION_2}.tar.gz"
        archive_v2 = create_kit_archive(tmp_path, config_v2, archive_name_v2)
        kit_service.save_kit(archive_v2)

        kit_path_v1 = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        kit_path_v2 = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION_2)
        assert kit_path_v1.exists()
        assert kit_path_v2.exists()

        kit_service.delete_kit_version(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert not kit_path_v1.exists()
        assert kit_path_v2.exists()
        assert kit_service.get_kit_path(KIT_OWNER, KIT_ID).exists()

    def test_delete_kit_version_not_found(self, kit_service: KitService):
        with pytest.raises(KitNotFoundError):
            kit_service.delete_kit_version(KIT_OWNER, KIT_ID, VALID_VERSION)

    def test_delete_kit_version_invalid_version(self, kit_service: KitService, create_saved_kit: KitMetadata):
         with pytest.raises(InvalidVersionError):
            kit_service.delete_kit_version(KIT_OWNER, KIT_ID, INVALID_VERSION)

    def test_delete_kit_success(self, kit_service: KitService, tmp_path: Path, sample_kit_config_dict: dict):
        archive_name_v1 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz"
        archive_v1 = create_kit_archive(tmp_path, sample_kit_config_dict, archive_name_v1)
        kit_service.save_kit(archive_v1)
        config_v2 = sample_kit_config_dict.copy(); config_v2["version"] = VALID_VERSION_2
        archive_name_v2 = f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION_2}.tar.gz"
        archive_v2 = create_kit_archive(tmp_path, config_v2, archive_name_v2)
        kit_service.save_kit(archive_v2)

        kit_id_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID)
        owner_path = kit_service.get_kit_path(KIT_OWNER, "")
        assert kit_id_path.exists()
        assert owner_path.exists()

        kit_service.delete_kit(KIT_OWNER, KIT_ID)
        assert not kit_id_path.exists()
        assert not owner_path.exists()

    def test_delete_kit_not_found(self, kit_service: KitService):
         with pytest.raises(KitNotFoundError):
            kit_service.delete_kit(KIT_OWNER, KIT_ID)

    # --- Registry Tests (using mocks) ---


    def test_get_registry_kits_no_registry_url(self, kit_service: KitService):
         with patch.dict(os.environ, clear=True):
             with pytest.raises(KitError, match="REGISTRY_URL environment variable not set"):
                 kit_service.get_registry_kits()

    def test_get_registry_kits_registry_error(self, kit_service: KitService, mock_httpx_client: MagicMock):
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection failed")
        with patch('httpx.Client', return_value=mock_httpx_client):
            with pytest.raises(RegistryError, match="Failed to get kits from registry"):
                kit_service.get_registry_kits()

    def test_install_kit_specific_version_success(self, kit_service: KitService, mock_httpx_client: MagicMock, tmp_path: Path, sample_kit_config_dict: dict):
        details_url = f"{REGISTRY_URL}/api/kits/{KIT_OWNER}/{KIT_ID}/{VALID_VERSION}"
        download_url = f"{REGISTRY_URL}/download/{KIT_OWNER}/{KIT_ID}/{VALID_VERSION}"
        details_response_json = {"downloadUrl": download_url}
        archive_io = create_kit_archive(tmp_path, sample_kit_config_dict, f"{KIT_OWNER}-{KIT_ID}-{VALID_VERSION}.tar.gz")
        archive_content = archive_io.getvalue()

        mock_httpx_client.get.side_effect = [
            create_mock_response(200, json_data=details_response_json, request_url=details_url),
            create_mock_response(200, content=archive_content, request_url=download_url)
        ]

        with patch('httpx.Client', return_value=mock_httpx_client):
            metadata = kit_service.install_kit(KIT_OWNER, KIT_ID, VALID_VERSION)

        assert metadata.owner == KIT_OWNER
        assert metadata.kit_id == KIT_ID
        assert metadata.version == VALID_VERSION
        kit_path = kit_service.get_kit_path(KIT_OWNER, KIT_ID, VALID_VERSION)
        assert kit_path.exists()

        assert mock_httpx_client.get.call_count == 2
        assert mock_httpx_client.get.call_args_list[0].args[0] == details_url
        assert mock_httpx_client.get.call_args_list[1].args[0] == download_url
