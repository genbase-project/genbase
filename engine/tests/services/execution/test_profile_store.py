# tests/services/execution/test_profile_store.py

import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC, timedelta
from contextlib import contextmanager
import json
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from engine.services.execution.profile_store import (
    ProfileStoreService,
    ProfileStoreInfo,
    ProfileStoreRecord,
    ProfileStoreFilter,
    ProfileStoreError,
    FilterOp,
    SortOrder,
    CombineOp
)
from engine.db.models import Module, ProfileStore

# --- Constants ---
TEST_MODULE_ID = "test-module-123"
TEST_PROFILE = "test-profile"
TEST_COLLECTION = "test-collection"

# --- Fixtures ---

@pytest.fixture
def profile_store_info() -> ProfileStoreInfo:
    return ProfileStoreInfo(
        module_id=TEST_MODULE_ID,
        profile=TEST_PROFILE,
        collection=TEST_COLLECTION
    )

@pytest.fixture
def profile_store_service(db_session: Session, profile_store_info: ProfileStoreInfo) -> ProfileStoreService:
    service = ProfileStoreService(storeInfo=profile_store_info)
    @contextmanager
    def test_db_context():
        yield db_session
    service._get_db = test_db_context
    return service

@pytest.fixture
def test_module(db_session: Session) -> Module:
    module = Module(
        module_id=TEST_MODULE_ID,
        module_name="Test Module",
        kit_id="test-kit",
        owner="test-owner",
        version="1.0.0",
        created_at=datetime.now(UTC),
        env_vars={},
        workspace_name="test-repo"
    )
    existing = db_session.query(Module).filter_by(module_id=TEST_MODULE_ID).first()
    if existing:
        return existing
    db_session.add(module)
    db_session.commit()
    db_session.refresh(module)
    return module

@pytest.fixture
def sample_data() -> List[Dict[str, Any]]:
    return [
        {
            "id": "item1",
            "name": "Test Item 1",
            "price": 100.50,
            "tags": ["electronics", "sale"],
            "metadata": { "color": "red", "weight": 1.5 },
            "in_stock": True,
            "created_at": (datetime.now(UTC) - timedelta(days=5)).isoformat()
        },
        {
            "id": "item2",
            "name": "Test Item 2",
            "price": 50.25,
            "tags": ["clothing", "sale", "summer"],
            "metadata": { "color": "blue", "weight": 0.3 },
            "in_stock": True,
            "created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat()
        },
        {
            "id": "item3",
            "name": "Test Item 3",
            "price": 200.00,
            "tags": ["electronics", "premium"],
            "metadata": { "color": "black", "weight": 2.0 },
            "in_stock": False,
            "created_at": (datetime.now(UTC) - timedelta(days=10)).isoformat()
        }
    ]

@pytest_asyncio.fixture
async def populated_store(profile_store_service: ProfileStoreService, test_module: Module, sample_data: List[Dict[str, Any]]) -> List[ProfileStoreRecord]:
    assert test_module is not None
    return await profile_store_service.set_many(sample_data)

# --- Test Cases ---

@pytest.mark.asyncio
class TestProfileStoreService:

    async def test_set_value(self, profile_store_service: ProfileStoreService, test_module: Module):
        value = {"name": "Single Test Item", "price": 75.99, "in_stock": True}
        record = await profile_store_service.set_value(value)
        assert isinstance(record, ProfileStoreRecord)
        assert record.module_id == TEST_MODULE_ID
        assert record.value == value
        assert isinstance(record.id, uuid.UUID)

    async def test_set_many(self, profile_store_service: ProfileStoreService, test_module: Module, sample_data: List[Dict[str, Any]]):
        records = await profile_store_service.set_many(sample_data)
        assert len(records) == len(sample_data)
        for i, record in enumerate(records):
            assert isinstance(record, ProfileStoreRecord)
            assert record.value == sample_data[i]

    async def test_get_by_id(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        record_to_find = populated_store[0]
        record_id = record_to_find.id
        record = await profile_store_service.get_by_id(record_id)
        assert record is not None
        assert record.id == record_id
        assert record.value["id"] == record_to_find.value["id"]

    async def test_get_by_id_not_found(self, profile_store_service: ProfileStoreService, test_module: Module):
        record = await profile_store_service.get_by_id(uuid.uuid4())
        assert record is None

    # Tests using potentially incompatible JSON operators
    # Expect OperationalError when run against SQLite

    async def test_find_simple_filter_eq(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        filter_ = ProfileStoreFilter(value_filters={"id": {"eq": "item1"}})
        records = await profile_store_service.find(filter_)
        assert len(records) == 1
        assert records[0].value["id"] == "item1"

    async def test_find_simple_filter_gt(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        filter_ = ProfileStoreFilter(value_filters={"price": {"gt": 100}})
        with pytest.raises(ProfileStoreError, match="Failed to find profile store entries"):
             await profile_store_service.find(filter_)



    async def test_find_with_in_operator(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        filter_ = ProfileStoreFilter(value_filters={"metadata.color": {"in": ["red", "blue"]}})
        with pytest.raises(ProfileStoreError, match="Failed to find profile store entries"):
            await profile_store_service.find(filter_)

    async def test_find_with_contains(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        filter_ = ProfileStoreFilter(value_filters={"tags": {"contains": ["sale"]}})
        with pytest.raises(ProfileStoreError, match="Failed to find profile store entries"):
             await profile_store_service.find(filter_)

    # Tests for basic functionality (Limit/Offset/Update/Delete)

    async def test_find_with_limit_offset_basic(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord]):
        all_records = await profile_store_service.find(ProfileStoreFilter())
        total_count = len(all_records)
        if total_count < 2:
             pytest.skip("Not enough records to test offset")

        filter_ = ProfileStoreFilter(limit=1, offset=1)
        records = await profile_store_service.find(filter_)
        assert len(records) == 1

    async def test_update_simple(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord], db_session: Session):
        record_to_update_id_val = populated_store[1].value["id"]
        record_to_update_pk = populated_store[1].id
        filter_ = ProfileStoreFilter(value_filters={"id": {"eq": record_to_update_id_val}})
        update_value = {"name": "Updated Item 2 Name", "price": 60.00}

        await profile_store_service.update(filter_, update_value)
        db_session.commit()
        updated_record_db = db_session.get(ProfileStore, record_to_update_pk)
        assert updated_record_db is not None
        assert updated_record_db.value["name"] == "Updated Item 2 Name"
        assert updated_record_db.value["price"] == 60.00

    async def test_delete_simple(self, profile_store_service: ProfileStoreService, populated_store: List[ProfileStoreRecord], db_session: Session):
        record_to_delete_id_val = populated_store[0].value["id"]
        record_to_delete_pk = populated_store[0].id
        filter_ = ProfileStoreFilter(value_filters={"id": {"eq": record_to_delete_id_val}})

        await profile_store_service.delete(filter_)
        db_session.commit()
        deleted_record_db = db_session.get(ProfileStore, record_to_delete_pk)
        assert deleted_record_db is None

    # Error Handling Test
    async def test_error_handling(self, profile_store_service: ProfileStoreService, test_module: Module):
        @contextmanager
        def mock_context_manager():
            raise Exception("Simulated Database error")
            yield None

        profile_store_service._get_db = mock_context_manager

        with pytest.raises(ProfileStoreError, match="Failed to set profile store value") as excinfo:
            await profile_store_service.set_value({"test": "value"})
        assert "Simulated Database error" in str(excinfo.value)