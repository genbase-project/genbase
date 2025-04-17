# src/genbase_agent_client/types.py

from typing import Optional, List, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid
from dataclasses import dataclass, field # Use dataclasses for simpler structures

# --- Data Structures Shared Between Engine and Client ---

@dataclass
class AgentContext:
    """Context for an agent operation, passed from Engine to Agent."""
    module_id: str
    profile: str
    user_input: str # The specific input for this request
    session_id: Optional[str] = field(default_factory=lambda: str(uuid.UUID(int=0)))

    # Make dataclass serializable if needed directly (or use asdict)
    # Consider using dataclasses-json if complex serialization needed:
    # from dataclasses_json import dataclass_json
    # @dataclass_json

# Using Pydantic for IncludeOptions as it has validation
IncludeType = Union[Literal["all", "none"], List[str]]

class IncludeOptions(BaseModel):
    """Options for what context/tools to include when setting agent context."""
    provided_tools: bool = False
    tools: IncludeType = "all"
    content_types: IncludeType = Field(default="none", description="Specifies allowed MIME types for agent output using <content> tags.")


    @field_validator('content_types', 'tools')
    @classmethod
    def validate_include_type(cls, value, info):
        field_name = info.field_name
        if isinstance(value, str) and value not in ("all", "none"):
            raise ValueError(f"'{field_name}' must be 'all', 'none', or list")
        elif not isinstance(value, (str, list)):
            raise TypeError(f"'{field_name}' must be str or list")
        elif isinstance(value, list) and not all(isinstance(item, str) for item in value):
            raise TypeError(f"Items in '{field_name}' list must be strings")
        return value

# Data structure for Profile Store Filters (matching the engine's definition)
# Use dataclasses here for simplicity, assuming validation happens server-side primarily.
class FilterOp: # Simple constants instead of Enum if preferred for client
    LTE = "lte"
    GT = "gt"
    LT = "lt" 
    GTE = "gte" 
    EQ = "eq"
    IN = "in"
    CONTAINS = "contains"

class SortOrder: 
    ASC = "asc"
    DESC = "desc"
    
class CombineOp:
    AND = "and"
    OR = "or"

@dataclass
class ProfileStoreFilter:
    """Filter for profile store queries (Client-side representation)."""
    value_filters: Optional[Dict[str, Dict[str, Any]]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: Optional[Dict[str, str]] = None # Use string for SortOrder
    sub_filters: List['ProfileStoreFilter'] = field(default_factory=list)
    combine_op: Optional[str] = None # Use string for CombineOp

    def __post_init__(self):
        # Basic validation if needed client-side
        if self.sort_by:
            for order in self.sort_by.values():
                if order not in (SortOrder.ASC, SortOrder.DESC):
                    raise ValueError(f"Invalid sort order: {order}")
        if self.combine_op and self.combine_op not in (CombineOp.AND, CombineOp.OR):
            raise ValueError(f"Invalid combine op: {self.combine_op}")

# --- Potentially add other shared types like ProfileStoreRecord if needed ---
# --- Or rely on receiving dicts from the server ---
@dataclass
class ProfileStoreRecord:
    """Client-side representation of a profile store record (optional)."""
    id: str # Keep as string from server
    module_id: str
    profile: str
    collection: str
    value: Dict[str, Any]
    created_at: str # Keep as string
    updated_at: str # Keep as string

# You might not need *all* engine types here, only those directly
# used in the BaseAgent interface or commonly used by agent developers.


@dataclass
class ProfileStoreInfo:
    """ProfileStore metadata"""
    module_id: str
    profile: str
    collection: str
