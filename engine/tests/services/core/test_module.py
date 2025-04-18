# tests/services/core/test_module.py

import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import io
import zipfile
from datetime import datetime, UTC
from contextlib import contextmanager
import shutil # Ensure shutil is imported

import networkx as nx
from sqlalchemy.orm import Session

from engine.services.core.module import (
    ModuleService,
    ModuleMetadata,
    ModuleError
)
from engine.services.storage.repository import WorkspaceService, WorkspaceNotFoundError
from engine.services.execution.state import StateService
from engine.services.core.kit import KitService, KitConfig
from engine.db.models import Module, Project, ProjectModuleMapping, ProvideType, ModuleProvide
from engine.utils.file import extract_zip

# --- Constants ---
TEST_PROJECT_ID = "prj-test-123"
TEST_OWNER = "test-owner"
TEST_KIT_ID = "test-kit"
TEST_VERSION = "1.0.0"
TEST_MODULE_ID_1 = "mod-abc"
TEST_MODULE_ID_2 = "mod-def"


# --- Fixtures ---

@pytest.fixture
def mock_repo_service() -> MagicMock:
    service = MagicMock(spec=WorkspaceService)
    service.create_repository = MagicMock()
    service.delete_repository = MagicMock()
    service.add_submodule = MagicMock()
    service.remove_submodule = MagicMock()
    return service

@pytest.fixture
def mock_state_service() -> MagicMock:
    service = MagicMock(spec=StateService)
    service.initialize_module = MagicMock()
    return service

@pytest.fixture
def mock_kit_service() -> MagicMock:
    service = MagicMock(spec=KitService)
    dummy_kit_config = MagicMock(spec=KitConfig)
    dummy_kit_config.owner = TEST_OWNER
    dummy_kit_config.id = TEST_KIT_ID
    dummy_kit_config.version = TEST_VERSION
    service.get_kit_config.return_value = dummy_kit_config
    return service

@pytest.fixture
def module_service(
    tmp_path: Path,
    db_session: Session,
    mock_repo_service: MagicMock,
    mock_state_service: MagicMock,
    mock_kit_service: MagicMock
) -> ModuleService:
    workspace_base = tmp_path / "kits"
    module_base = tmp_path / "module_kits"

    service = ModuleService(
        workspace_base=str(workspace_base),
        module_base=str(module_base),
        repo_service=mock_repo_service,
        state_service=mock_state_service,
        kit_service=mock_kit_service
    )

    # Create a context manager factory
    @contextmanager
    def test_db_context():
        yield db_session
        
    # Override the _get_db method to return our context manager factory
    service._get_db = test_db_context

    dummy_workspace = workspace_base / TEST_OWNER / TEST_KIT_ID / TEST_VERSION / "workspace"
    dummy_workspace.mkdir(parents=True, exist_ok=True)
    (dummy_workspace / "dummy_file.txt").touch()

    return service

@pytest.fixture
def create_db_project(db_session: Session) -> Project:
    project = Project(id=TEST_PROJECT_ID, name="Test Project", created_at=datetime.now(UTC))
    # Defensive check in case previous test run failed rollback
    existing = db_session.get(Project, TEST_PROJECT_ID)
    if existing:
        return existing
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project

@pytest.fixture
def create_db_module(db_session: Session, create_db_project: Project) -> Module:
    created_at_dt = datetime.now(UTC) # Use datetime object
    module = Module(
        module_id=TEST_MODULE_ID_1,
        module_name="Test Module 1",
        kit_id=TEST_KIT_ID,
        owner=TEST_OWNER,
        version=TEST_VERSION,
        created_at=created_at_dt,
        env_vars={"KEY": "VALUE"},
        repo_name=f"{TEST_MODULE_ID_1}-repo"
    )
    # Defensive check
    existing = db_session.get(Module, TEST_MODULE_ID_1)
    if existing:
        # Ensure mapping exists if module does
        mapping = db_session.get(ProjectModuleMapping, (create_db_project.id, existing.module_id))
        if not mapping:
             mapping = ProjectModuleMapping(project_id=create_db_project.id, module_id=existing.module_id, path="test.module.one", created_at=existing.created_at, updated_at=existing.created_at)
             db_session.add(mapping)
             db_session.commit()
        return existing


    mapping = ProjectModuleMapping(
        project_id=create_db_project.id,
        module_id=module.module_id,
        path="test.module.one",
        created_at=created_at_dt,
        updated_at=created_at_dt
    )
    db_session.add(module)
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(module)
    db_session.refresh(mapping) # Refresh mapping too
    return module

@pytest.fixture
def create_db_module_2(db_session: Session, create_db_project: Project) -> Module:
    created_at_dt = datetime.now(UTC) # Use datetime object
    module = Module(
        module_id=TEST_MODULE_ID_2,
        module_name="Test Module 2",
        kit_id=TEST_KIT_ID,
        owner=TEST_OWNER,
        version=TEST_VERSION,
        created_at=created_at_dt,
        env_vars={},
        repo_name=f"{TEST_MODULE_ID_2}-repo"
    )
    # Defensive check
    existing = db_session.get(Module, TEST_MODULE_ID_2)
    if existing:
         mapping = db_session.get(ProjectModuleMapping, (create_db_project.id, existing.module_id))
         if not mapping:
             mapping = ProjectModuleMapping(project_id=create_db_project.id, module_id=existing.module_id, path="test.module.two", created_at=existing.created_at, updated_at=existing.created_at)
             db_session.add(mapping)
             db_session.commit()
         return existing

    mapping = ProjectModuleMapping(
        project_id=create_db_project.id,
        module_id=module.module_id,
        path="test.module.two",
        created_at=created_at_dt,
        updated_at=created_at_dt
    )
    db_session.add(module)
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(module)
    db_session.refresh(mapping)
    return module

# Helper functions for module provides tests
def create_module_provide_in_db(db_session, provider_id, receiver_id, resource_type, description=None):
    """Create a ModuleProvide instance directly in the database"""
    now = datetime.now(UTC)
    provide = ModuleProvide(
        provider_id=provider_id,
        receiver_id=receiver_id,
        resource_type=resource_type,
        description=description,
        created_at=now,
        updated_at=now
    )
    db_session.add(provide)
    db_session.commit()
    return provide


# --- Test Cases ---

class TestModuleService:

    def test_validate_path(self, module_service: ModuleService):
        assert module_service._validate_path("valid.path") is True
        assert module_service._validate_path("a.b.c.1") is True
        assert module_service._validate_path("single") is True
        assert module_service._validate_path("invalid path") is False
        assert module_service._validate_path("invalid-path") is False
        assert module_service._validate_path(".start") is False
        assert module_service._validate_path("end.") is False
        assert module_service._validate_path("a..b") is False

    @patch('engine.services.core.module.generate_readable_uid', return_value='new-mod-id')
    @patch('engine.services.core.module.datetime')
    def test_create_module_success(self, mock_datetime, mock_generate_uid, module_service: ModuleService, create_db_project: Project, mock_repo_service: MagicMock, mock_state_service: MagicMock, db_session: Session):
        # Mock datetime to return a real datetime object, not a string
        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.UTC = UTC
        
        project_id = create_db_project.id
        owner = TEST_OWNER
        kit_id = TEST_KIT_ID
        version = TEST_VERSION
        env_vars = {"API_KEY": "123"}
        path = "new.module.path"
        module_name = "New Module"

        metadata = module_service.create_module(project_id, owner, kit_id, version, env_vars, path, module_name)

        assert isinstance(metadata, ModuleMetadata)
        assert metadata.module_id == 'new-mod-id'
        assert metadata.project_id == project_id
        assert metadata.owner == owner
        assert metadata.kit_id == kit_id
        assert metadata.version == version
        assert metadata.env_vars == env_vars
        assert metadata.path == path
        assert metadata.module_name == module_name
        assert metadata.repo_name == f"{metadata.module_id}"

        # Verify DB state
        db_module = db_session.get(Module, metadata.module_id)
        assert db_module is not None
        assert db_module.module_name == module_name
        db_mapping = db_session.get(ProjectModuleMapping, (project_id, metadata.module_id))
        assert db_mapping is not None
        assert db_mapping.path == path

        mock_repo_service.create_repository.assert_called_once_with(
            repo_name=metadata.repo_name,
            content_file=ANY,
            filename="workspace.zip",
            extract_func=extract_zip
        )
        mock_state_service.initialize_module.assert_called_once_with(metadata.module_id)

    def test_create_module_invalid_path(self, module_service: ModuleService, create_db_project: Project):
        with pytest.raises(ModuleError, match="Invalid path format"):
            module_service.create_module(create_db_project.id, TEST_OWNER, TEST_KIT_ID, TEST_VERSION, {}, "invalid path")

    def test_create_module_workspace_not_found(self, module_service: ModuleService, create_db_project: Project):
        if module_service.workspace_base.exists():
             shutil.rmtree(module_service.workspace_base)
        with pytest.raises(ModuleError, match="Workspace not found"):
            module_service.create_module(create_db_project.id, TEST_OWNER, TEST_KIT_ID, TEST_VERSION, {}, "a.b.c")

    def test_update_module_path_success(self, module_service: ModuleService, create_db_module: Module, db_session: Session):
        new_path = "updated.module.path"
        module_id = create_db_module.module_id
        project_id = create_db_module.project_mappings[0].project_id

        module_service.update_module_path(module_id, project_id, new_path)

        # Query directly for the mapping
        mapping = db_session.get(ProjectModuleMapping, (project_id, module_id))
        assert mapping.path == new_path

    def test_get_project_modules(self, module_service: ModuleService, create_db_module: Module):
        project_id = create_db_module.project_mappings[0].project_id
        modules = module_service.get_project_modules(project_id)
        assert len(modules) >= 1 # Allow for potential default project modules if tests run together
        assert any(m.module_id == create_db_module.module_id for m in modules)
        test_module_meta = next(m for m in modules if m.module_id == create_db_module.module_id)
        assert isinstance(test_module_meta, ModuleMetadata)
        assert test_module_meta.path == "test.module.one"




    def test_delete_module_success(self, module_service: ModuleService, create_db_module: Module, db_session: Session, mock_repo_service: MagicMock):
        module_id = create_db_module.module_id
        repo_name = create_db_module.repo_name
        project_id = create_db_module.project_mappings[0].project_id
        assert db_session.get(Module, module_id) is not None
        assert db_session.get(ProjectModuleMapping, (project_id, module_id)) is not None

        module_service.delete_module(module_id)

        assert db_session.get(Module, module_id) is None
        # Cascading should delete the mapping too, verify this way
        assert db_session.query(ProjectModuleMapping).filter_by(module_id=module_id).count() == 0
        mock_repo_service.delete_repository.assert_called_once_with(repo_name)



    def test_get_module_metadata_success(self, module_service: ModuleService, create_db_module: Module):
        metadata = module_service.get_module_metadata(create_db_module.module_id)
        assert isinstance(metadata, ModuleMetadata)
        assert metadata.module_id == create_db_module.module_id
        assert metadata.module_name == create_db_module.module_name
        assert metadata.path == "test.module.one"

    def test_get_module_metadata_not_found(self, module_service: ModuleService):
        with pytest.raises(ModuleError, match="Module non-existent-mod not found"):
            module_service.get_module_metadata("non-existent-mod")

    def test_update_module_name_success(self, module_service: ModuleService, create_db_module: Module, db_session: Session):
        new_name = "Updated Module Name"
        metadata = module_service.update_module_name(create_db_module.module_id, new_name)
        assert metadata.module_name == new_name

        # Query directly from DB to verify
        updated_module = db_session.get(Module, create_db_module.module_id)
        assert updated_module.module_name == new_name

    def test_update_module_env_var_success(self, module_service: ModuleService, create_db_module: Module, db_session: Session):
        var_name = "NEW_VAR"
        var_value = "new_value"
        metadata = module_service.update_module_env_var(create_db_module.module_id, var_name, var_value)
        assert metadata.env_vars[var_name] == var_value
        assert metadata.env_vars["KEY"] == "VALUE"

        # Query directly from DB to verify
        updated_module = db_session.get(Module, create_db_module.module_id)
        assert updated_module.env_vars[var_name] == var_value

    def test_get_module_kit_config(self, module_service: ModuleService, create_db_module: Module, mock_kit_service: MagicMock):
        config = module_service.get_module_kit_config(create_db_module.module_id)
        assert isinstance(config, MagicMock)
        mock_kit_service.get_kit_config.assert_called_once_with(
            owner=TEST_OWNER,
            kit_id=TEST_KIT_ID,
            version=TEST_VERSION
        )

    # Tests that would use ModuleProvide methods are omitted to simplify
    # If we wish to test ModuleProvide functionality, we would need to 
    # create method wrappers that handle the context manager properly