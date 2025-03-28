import json
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

from sqlalchemy import Float, asc, desc, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from engine.db.models import Module, ProfileStore
from engine.db.session import SessionLocal
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

class FilterOp(str, Enum):
    LTE = "lte"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    EQ = "eq"
    IN = "in"
    CONTAINS = "contains"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class CombineOp(str, Enum):
    AND = "and"
    OR = "or"

@dataclass
class ProfileStoreFilter:
    """Filter for profile store queries"""
    value_filters: Optional[Dict[str, Dict[str, Any]]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: Optional[Dict[str, SortOrder]] = None
    sub_filters: List['ProfileStoreFilter'] = field(default_factory=list)
    combine_op: Optional[CombineOp] = None

    def __and__(self, other: 'ProfileStoreFilter') -> 'ProfileStoreFilter':
        """Combine two filters with AND operation"""
        return ProfileStoreFilter(
            sub_filters=[self, other],
            combine_op=CombineOp.AND
        )

    def __or__(self, other: 'ProfileStoreFilter') -> 'ProfileStoreFilter':
        """Combine two filters with OR operation"""
        return ProfileStoreFilter(
            sub_filters=[self, other],
            combine_op=CombineOp.OR
        )




@dataclass
class ProfileStoreInfo:
    """ProfileStore metadata"""
    module_id: str
    profile: str
    collection: str


@dataclass
class ProfileStoreRecord:
    """ProfileStore metadata"""
    id: uuid.UUID
    module_id: str
    profile: str
    collection: str
    value: Dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, store: ProfileStore) -> 'ProfileStoreRecord':
        """Convert SQLAlchemy ProfileStore object to ProfileStoreMetadata"""
        return cls(
            id=store.id,
            module_id=store.module_id,
            profile=store.profile,
            collection=store.collection,
            value=store.value,
            created_at=store.created_at.isoformat(),
            updated_at=store.updated_at.isoformat()
        )


class ProfileStoreError(Exception):
    """Base exception for profile store errors"""
    pass


class ProfileStoreService:
    """Service for managing profile store"""

    def __init__(self, storeInfo: ProfileStoreInfo):
        """Initialize Profile store service"""
        self.storeInfo = storeInfo

    def _get_db(self) -> Session:
        return SessionLocal()


    def _build_query(self, db: Session, filter_: ProfileStoreFilter):
        """Build query from filter"""
        query = db.query(ProfileStore)

        query = query.filter(ProfileStore.module_id == self.storeInfo.module_id)
        query = query.filter(ProfileStore.profile == self.storeInfo.profile)
        query = query.filter(ProfileStore.collection == self.storeInfo.collection)

        if filter_.value_filters:
            for field, ops in filter_.value_filters.items():
                for op, value in ops.items():
                    # Handle nested JSON fields
                    json_path = field.split('.')
                    if len(json_path) > 1:
                        # For nested fields, use the -> operator for all but the last field
                        path_expr = '->'.join([f"'{p}'" for p in json_path[:-1]])
                        last_field = json_path[-1]
                        field_expr = f"value->{path_expr}->>'{last_field}'"
                    else:
                        field_expr = f"value->>'{field}'"

                    param_name = f"value_{field.replace('.', '_')}"

                    if op == FilterOp.EQ:
                        query = query.filter(
                            text(f"{field_expr} = :{param_name}")
                        ).params(**{param_name: str(value)})
                    elif op == FilterOp.LT:
                        query = query.filter(
                            text(f"({field_expr})::float < :{param_name}")
                        ).params(**{param_name: float(value)})
                    elif op == FilterOp.LTE:
                        query = query.filter(
                            text(f"({field_expr})::float <= :{param_name}")
                        ).params(**{param_name: float(value)})
                    elif op == FilterOp.GT:
                        query = query.filter(
                            text(f"({field_expr})::float > :{param_name}")
                        ).params(**{param_name: float(value)})
                    elif op == FilterOp.GTE:
                        query = query.filter(
                            text(f"({field_expr})::float >= :{param_name}")
                        ).params(**{param_name: float(value)})
                    elif op == FilterOp.IN:
                        query = query.filter(
                            text(f"{field_expr} = ANY(:{param_name})")
                        ).params(**{param_name: [str(v) for v in value]})
                    elif op == FilterOp.CONTAINS:
                        if isinstance(value, list):
                            # For array contains
                            query = query.filter(
                                text(f"value->'{field}' ?& array[:{param_name}]")
                            ).params(**{param_name: value})
                        else:
                            # For object contains
                            json_path = {field: value}
                            query = query.filter(
                                text("value @> :value::jsonb")
                            ).params(value=json.dumps(json_path))

        if filter_.sort_by:
            for field, order in filter_.sort_by.items():
                # Handle nested JSON fields in sorting
                json_path = field.split('.')
                if len(json_path) > 1:
                    path_expr = '->'.join([f"'{p}'" for p in json_path[:-1]])
                    last_field = json_path[-1]
                    field_expr = f"value->{path_expr}->>'{last_field}'"
                else:
                    field_expr = f"value->>'{field}'"

                direction = desc if order == SortOrder.DESC else asc
                query = query.order_by(direction(text(field_expr)))

        if filter_.offset is not None:
            query = query.offset(filter_.offset)
        
        if filter_.limit is not None:
            query = query.limit(filter_.limit)

        return query

    async def get_by_id(self, id: uuid.UUID) -> Optional[ProfileStoreRecord]:
        """Get a single store entry by ID"""
        try:
            with self._get_db() as db:
                store = db.query(ProfileStore).filter(ProfileStore.id == id).first()
                return ProfileStoreRecord.from_orm(store) if store else None
        except Exception as e:
            raise ProfileStoreError(f"Failed to get profile store by ID: {str(e)}")

    async def set_value(
        self,
        value: Dict[str, Any]
    ) -> ProfileStoreRecord:
        """Set a single value"""
        try:
            with self._get_db() as db:
                store = ProfileStore(
                    module_id=self.storeInfo.module_id,
                    profile=self.storeInfo.profile,
                    collection=self.storeInfo.collection,
                    value=value,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                db.add(store)
                db.commit()
                db.refresh(store)
                return ProfileStoreRecord.from_orm(store)
        except Exception as e:
            raise ProfileStoreError(f"Failed to set profile store value: {str(e)}")

    async def set_many(
        self,
        values: List[Dict[str, Any]]
    ) -> List[ProfileStoreRecord]:
        """Set multiple values"""
        try:
            with self._get_db() as db:
                stores = []
                for value_data in values:
                    store = ProfileStore(
                        module_id=self.storeInfo.module_id,
                        profile=self.storeInfo.profile,
                        collection=self.storeInfo.collection,
                        value=value_data,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC)
                    )
                    stores.append(store)
                
                db.add_all(stores)
                db.commit()
                for store in stores:
                    db.refresh(store)
                
                return [ProfileStoreRecord.from_orm(store) for store in stores]
        except Exception as e:
            raise ProfileStoreError(f"Failed to set multiple profile store values: {str(e)}")

    async def find(self, filter_: ProfileStoreFilter) -> List[ProfileStoreRecord]:
        """Find store entries using filter"""
        try:
            with self._get_db() as db:
                query = self._build_query(db, filter_)
                stores = query.all()
                return [ProfileStoreRecord.from_orm(store) for store in stores]
        except Exception as e:
            raise ProfileStoreError(f"Failed to find profile store entries: {str(e)}")

    async def update(
        self,
        filter_: ProfileStoreFilter,
        value: Dict[str, Any]
    ) -> int:
        """Update values using filter"""
        try:
            with self._get_db() as db:
                query = self._build_query(db, filter_)
                stores = query.all()
                
                for store in stores:
                    store.value = value
                    store.updated_at = datetime.now(UTC)
                
                db.commit()
                return len(stores)
        except Exception as e:
            raise ProfileStoreError(f"Failed to update profile store entries: {str(e)}")

    async def delete(self, filter_: ProfileStoreFilter) -> int:
        """Delete entries using filter"""
        try:
            with self._get_db() as db:
                query = self._build_query(db, filter_)
                stores = query.all()
                
                for store in stores:
                    db.delete(store)
                
                db.commit()
                return len(stores)
        except Exception as e:
            raise ProfileStoreError(f"Failed to delete profile store entries: {str(e)}")


# # Add at the end of the file
# async def test_profile_store():
#     """Advanced test suite with complex edge cases and comprehensive scenarios"""
    
#     service = ProfileStoreService(
#         storeInfo=ProfileStoreInfo(
#             module_id="test_module",
#             profile="test_profile",
#             collection="test_collection"
#         )
#     )

#     # Setup
#     with service._get_db() as db:
#         test_module = Module(
#             module_id="test_module",
#             module_name="Test Module",
#             kit_id="test_kit",
#             owner="test_owner",
#             version="1.0.0",
#             created_at=datetime.now(UTC),
#             env_vars={},
#             repo_name="test_repo"
#         )
#         db.add(test_module)
#         db.commit()

#     # Test 1: Complex Nested Data Structures
#     print("\nTest 1: Testing complex nested data structures...")
#     try:
#         complex_data = [
#             {
#                 "metadata": {
#                     "version": "2.0.1",
#                     "environment": {
#                         "name": "production",
#                         "region": "us-west-2",
#                         "replicas": 3
#                     },
#                     "tags": ["critical", "ml-model", "high-priority"]
#                 },
#                 "metrics": {
#                     "accuracy": 0.956,
#                     "precision": 0.934,
#                     "recall": 0.945,
#                     "f1_score": 0.939,
#                     "latency_ms": 245
#                 },
#                 "status": {
#                     "code": "SUCCESS",
#                     "details": {
#                         "steps_completed": 5,
#                         "total_steps": 5,
#                         "warnings": []
#                     }
#                 },
#                 "timestamps": {
#                     "started_at": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
#                     "completed_at": datetime.now(UTC).isoformat()
#                 }
#             },
#             {
#                 "metadata": {
#                     "version": "2.0.0",
#                     "environment": {
#                         "name": "staging",
#                         "region": "eu-west-1",
#                         "replicas": 2
#                     },
#                     "tags": ["development", "ml-model"]
#                 },
#                 "metrics": {
#                     "accuracy": 0.923,
#                     "precision": 0.912,
#                     "recall": 0.934,
#                     "f1_score": 0.923,
#                     "latency_ms": 189
#                 },
#                 "status": {
#                     "code": "WARNING",
#                     "details": {
#                         "steps_completed": 5,
#                         "total_steps": 5,
#                         "warnings": ["High memory usage detected"]
#                     }
#                 },
#                 "timestamps": {
#                     "started_at": (datetime.now(UTC) - timedelta(minutes=45)).isoformat(),
#                     "completed_at": datetime.now(UTC).isoformat()
#                 }
#             }
#         ]
#         stores = await service.set_many(complex_data)
#         print(f"Success: Created {len(stores)} stores with complex nested data")
#     except Exception as e:
#         print(f"Failed: {str(e)}")

#     # Test 2: Advanced Filtering with Multiple Nested Conditions
#     print("\nTest 2: Testing advanced filtering with multiple nested conditions...")
#     try:
#         filter1 = ProfileStoreFilter(
#             value_filters={
#                 "metrics.accuracy": {"gte": 0.93},
#                 "metrics.latency_ms": {"lt": 200}
#             }
#         )
#         filter2 = ProfileStoreFilter(
#             value_filters={
#                 "metadata.environment.name": {"in": ["production", "staging"]},
#                 "status.code": {"eq": "SUCCESS"}
#             }
#         )
#         filter3 = ProfileStoreFilter(
#             value_filters={
#                 "metadata.tags": {"contains": ["ml-model"]},
#                 "status.details.warnings": {"contains": []}
#             }
#         )
        
#         combined_filter = (filter1 | filter2) & filter3
#         results = await service.find(combined_filter)
#         print(f"Success: Found {len(results)} stores matching complex nested criteria")
#     except Exception as e:
#         print(f"Failed: {str(e)}")

#     # Test 3: Edge Cases and Special Characters
#     print("\nTest 3: Testing edge cases and special characters...")
#     try:
#         edge_cases = [
#             {
#                 "special_chars": "!@#$%^&*()",
#                 "empty_array": [],
#                 "null_value": None,
#                 "unicode_text": "こんにちは世界",
#                 "very_long_text": "x" * 1000,
#                 "nested": {
#                     "empty_object": {},
#                     "zero_values": {
#                         "integer": 0,
#                         "float": 0.0,
#                         "string": ""
#                     }
#                 }
#             }
#         ]
#         stores = await service.set_many(edge_cases)
#         print(f"Success: Created {len(stores)} stores with edge cases")
#     except Exception as e:
#         print(f"Failed: {str(e)}")

#     # Test 4: Testing complex updates with conditional logic...
#     print("\nTest 4: Testing complex updates with conditional logic...")
#     try:
#         filter_ = ProfileStoreFilter(
#             value_filters={
#                 "metrics.accuracy": {"gte": 0.92},
#                 "metrics.latency_ms": {"lte": 200},
#                 "status.code": {"in": ["SUCCESS", "WARNING"]},
#                 "metadata.environment.replicas": {"gt": 1}
#             }
#         )
        
#         update_value = {
#             "status": {
#                 "code": "OPTIMIZED",
#                 "details": {
#                     "optimization_history": [{
#                         "timestamp": datetime.now(UTC).isoformat(),
#                         "changes": ["Reduced latency", "Increased replicas"],
#                         "metrics_delta": {
#                             "latency_improvement": "15%",
#                             "resource_usage": "-10%"
#                         }
#                     }]
#                 }
#             },
#             "metadata": {
#                 "tags": ["optimized", "ml-model"],
#                 "last_updated": datetime.now(UTC).isoformat()
#             }
#         }
        
#         updated_count = await service.update(filter_, update_value)
#         print(f"Success: Updated {updated_count} stores with complex conditions")
#     except Exception as e:
#         print(f"Failed: {str(e)}")

#     # Test 5: Stress Testing with Large Dataset and Complex Queries
#     print("\nTest 5: Stress testing with large dataset and complex queries...")
#     try:
#         # Generate 1000 records with random but realistic data
#         large_dataset = []
#         for i in range(1000):
#             timestamp = datetime.now(UTC) - timedelta(days=random.randint(0, 30))
#             accuracy = random.uniform(0.85, 0.99)
#             latency = random.randint(100, 500)
            
#             record = {
#                 "run_id": str(uuid.uuid4()),
#                 "metadata": {
#                     "version": f"1.{random.randint(0, 9)}.{random.randint(0, 99)}",
#                     "environment": {
#                         "name": random.choice(["prod", "staging", "dev"]),
#                         "region": random.choice(["us-west-2", "us-east-1", "eu-west-1"]),
#                         "replicas": random.randint(1, 5)
#                     },
#                     "batch_size": random.choice([32, 64, 128, 256])
#                 },
#                 "metrics": {
#                     "accuracy": accuracy,
#                     "latency_ms": latency,
#                     "throughput": random.randint(1000, 5000)
#                 },
#                 "status": {
#                     "code": random.choice(["SUCCESS", "WARNING", "ERROR"]),
#                     "timestamp": timestamp.isoformat()
#                 }
#             }
#             large_dataset.append(record)
        
#         stores = await service.set_many(large_dataset)
#         print(f"Success: Created {len(stores)} stores for stress testing")

#         # Complex query with multiple conditions
#         start_time = time.time()
#         filter_ = ProfileStoreFilter(
#             value_filters={
#                 "metrics.accuracy": {"gte": 0.95},
#                 "metrics.latency_ms": {"lte": 300},
#                 "metadata.environment.name": {"eq": "prod"},  # Changed to eq instead of in
#                 "metadata.batch_size": {"gte": 64},
#                 "status.code": {"eq": "SUCCESS"}
#             },
#             sort_by={"metrics.accuracy": SortOrder.DESC, "metrics.latency_ms": SortOrder.ASC},
#             limit=50,
#             offset=10
#         )
        
#         results = await service.find(filter_)
#         query_time = time.time() - start_time
#         print(f"Success: Complex query executed in {query_time:.2f} seconds, found {len(results)} results")
#     except Exception as e:
#         print(f"Failed: {str(e)}")
#     # Cleanup
#     try:
#         with service._get_db() as db:
#             db.query(Module).filter_by(module_id="test_module").delete()
#             db.commit()
#     except Exception as e:
#         print(f"Failed to cleanup: {str(e)}")

# if __name__ == "__main__":
#     import asyncio
#     import random
#     import time
#     from datetime import timedelta
#     asyncio.run(test_profile_store())