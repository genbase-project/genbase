# tests/services/core/test_api_key.py

from contextlib import contextmanager
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC, timedelta
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

# Import service and models
from engine.services.core.api_key import ApiKeyService
from engine.db.models import Module, ModuleApiKey # Import Module as well due to FK

# --- Test Fixtures ---

@pytest.fixture
def create_test_module(db_session: Session) -> Module:
    """Fixture to create a necessary Module record."""
    module = Module(
        module_id="test-module-1",
        module_name="Test Module One",
        kit_id="test-kit",
        owner="test-owner",
        version="1.0.0",
        created_at=datetime.now(UTC),
        env_vars={},
        repo_name="test-module-1-repo"
    )
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module

@pytest.fixture
def api_key_service(db_session: Session) -> ApiKeyService:
    service = ApiKeyService()
    
    def get_test_db():
        @contextmanager
        def test_db_context():
            try:
                yield db_session
            finally:
                pass
        return test_db_context()
    
    service._get_db = get_test_db
    return service
# --- Test Cases ---

class TestApiKeyService:

    def test_create_api_key_new(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        description = "Test key description"

        created_key = api_key_service.create_api_key(module_id, description)

        assert isinstance(created_key, ModuleApiKey)
        assert created_key.module_id == module_id
        assert created_key.description == description
        assert created_key.is_active is True
        assert created_key.api_key.startswith("mk_")
        assert created_key.created_at is not None
        assert created_key.last_used_at is None

        # Verify in DB
        db_key = db_session.get(ModuleApiKey, created_key.id)
        assert db_key is not None
        assert db_key.api_key == created_key.api_key

    def test_create_api_key_revokes_old(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id

        # Create first key
        key1 = api_key_service.create_api_key(module_id, "Key 1")
        assert key1.is_active is True

        # Create second key for the same module
        key2 = api_key_service.create_api_key(module_id, "Key 2")
        assert key2.is_active is True
        assert key1.id != key2.id

        # Verify first key is now inactive in DB
        db_session.expire(key1) # Ensure we get fresh data from DB
        db_key1 = db_session.get(ModuleApiKey, key1.id)
        assert db_key1 is not None
        assert db_key1.is_active is False

        # Verify second key is active in DB
        db_key2 = db_session.get(ModuleApiKey, key2.id)
        assert db_key2 is not None
        assert db_key2.is_active is True

    def test_get_api_key_exists_active(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        created_key = api_key_service.create_api_key(module_id)

        retrieved_key = api_key_service.get_api_key(module_id)

        assert retrieved_key is not None
        assert retrieved_key.id == created_key.id
        assert retrieved_key.api_key == created_key.api_key
        assert retrieved_key.is_active is True

    def test_get_api_key_exists_inactive(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        # Manually create an inactive key
        inactive_key = ModuleApiKey(
            id=uuid.uuid4(),
            module_id=module_id,
            api_key=ModuleApiKey.generate_key(),
            is_active=False,
            created_at=datetime.now(UTC)
        )
        db_session.add(inactive_key)
        db_session.commit()

        retrieved_key = api_key_service.get_api_key(module_id)
        assert retrieved_key is None

    def test_get_api_key_not_found(self, api_key_service: ApiKeyService, create_test_module: Module):
        retrieved_key = api_key_service.get_api_key("non-existent-module")
        assert retrieved_key is None

    def test_revoke_api_key_success(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        key = api_key_service.create_api_key(module_id)
        assert key.is_active is True

        result = api_key_service.revoke_api_key(module_id)
        assert result is True

        # Verify in DB
        db_session.expire(key)
        db_key = db_session.get(ModuleApiKey, key.id)
        assert db_key is not None
        assert db_key.is_active is False

    def test_revoke_api_key_no_active_key(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        # Ensure no active key exists (either none or only inactive)
        inactive_key = ModuleApiKey(
            id=uuid.uuid4(),
            module_id=module_id,
            api_key=ModuleApiKey.generate_key(),
            is_active=False,
            created_at=datetime.now(UTC)
        )
        db_session.add(inactive_key)
        db_session.commit()

        result = api_key_service.revoke_api_key(module_id)
        assert result is False

    def test_validate_api_key_success(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        key = api_key_service.create_api_key(module_id)
        assert key.last_used_at is None

        # Simulate time passing
        original_creation_time = key.created_at
        db_session.commit() # Commit creation before validation updates timestamp

        validated_module_id = api_key_service.validate_api_key(key.api_key)

        assert validated_module_id == module_id

        # Verify last_used_at is updated in DB
        db_session.expire(key)
        db_key = db_session.get(ModuleApiKey, key.id)
        assert db_key is not None
        assert db_key.last_used_at is not None
        assert db_key.last_used_at > original_creation_time

    def test_validate_api_key_inactive(self, api_key_service: ApiKeyService, db_session: Session, create_test_module: Module):
        module_id = create_test_module.module_id
        inactive_key = ModuleApiKey(
            id=uuid.uuid4(),
            module_id=module_id,
            api_key=ModuleApiKey.generate_key(),
            is_active=False,
            created_at=datetime.now(UTC)
        )
        db_session.add(inactive_key)
        db_session.commit()

        validated_module_id = api_key_service.validate_api_key(inactive_key.api_key)
        assert validated_module_id is None

    def test_validate_api_key_invalid(self, api_key_service: ApiKeyService, create_test_module: Module):
        validated_module_id = api_key_service.validate_api_key("invalid_key_string")
        assert validated_module_id is None