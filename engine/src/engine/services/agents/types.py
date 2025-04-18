from dataclasses import dataclass
from typing import List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, field_validator

from engine.services.core.module import ModuleService
from engine.services.execution.agent_execution import AgentRunnerService
from engine.services.execution.model import ModelService
from engine.services.execution.profile import ProfileService
from engine.services.execution.state import StateService
from engine.services.storage.workspace import WorkspaceService


@dataclass
class AgentServices:
    """Essential services required by all agents"""
    model_service: ModelService     # For LLM interactions
    profile_service: ProfileService  # For profile execution
    module_service: ModuleService   # For module management
    state_service: StateService     # For agent state management
    workspace_service: WorkspaceService       # For workspace operations
    agent_runner_service: AgentRunnerService  # For running agent tasks



IncludeType = Union[Literal["all", "none"], List[str]]
TModel = TypeVar('TModel', bound=BaseModel)

class IncludeOptions(BaseModel):
    provided_tools: bool = False
    elements: IncludeType = "all"
    tools: IncludeType = "all"
    
    @field_validator('elements', 'tools')
    @classmethod
    def validate_include_type(cls, value, info):
        field_name = info.field_name
        if isinstance(value, str) and value not in ("all", "none"):
            raise ValueError(
                f"Invalid value for '{field_name}': '{value}'. "
                f"Must be 'all', 'none', or a list of strings."
            )
        elif not isinstance(value, str) and not isinstance(value, list):
            raise TypeError(
                f"Invalid type for '{field_name}': {type(value)}. "
                f"Must be 'str' ('all' or 'none') or 'list'."
            )
        elif isinstance(value, list) and not all(isinstance(item, str) for item in value):
            raise TypeError(
                f"Invalid type within '{field_name}' list. "
                f"All items in the list must be strings."
            )
        return value



