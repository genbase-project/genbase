# tests/services/execution/test_internal_actions.py

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional, Literal

from engine.services.execution.internal_actions import InternalActionManager
from engine.services.execution.action import FunctionMetadata

# --- Sample Functions for Testing ---

def sync_action_simple(name: str, age: int = 30) -> str:
    """Simple synchronous action."""
    return f"Hello {name}, age {age}"

async def async_action_complex(items: List[Dict[str, Any]], config: Optional[Dict] = None) -> int:
    """Complex asynchronous action."""
    count = len(items)
    if config:
        count += config.get("bonus", 0)
    return count

def action_no_docstring(x):
    pass

def action_with_params_docstring(value: float):
    """Action with parameter docs.

    Args:
        value: The float value to process.
    """
    return value * 2

# --- Fixtures ---

@pytest.fixture
def action_manager() -> InternalActionManager:
    """Provides a clean InternalActionManager instance for each test."""
    manager = InternalActionManager()
    # Clear any potentially registered actions from previous tests if needed
    manager.clear_actions()
    return manager

# --- Test Cases ---

class TestInternalActionManager:

    def test_init(self, action_manager: InternalActionManager):
        assert isinstance(action_manager._internal_actions, dict)
        assert isinstance(action_manager._internal_action_metadata, dict)
        assert len(action_manager._internal_actions) == 0
        assert len(action_manager._internal_action_metadata) == 0

    def test_register_action_success(self, action_manager: InternalActionManager):
        name = "test_sync"
        func = sync_action_simple
        desc = "Explicit Description"
        action_manager.register_action(name, func, desc)

        assert name in action_manager._internal_actions
        assert action_manager._internal_actions[name] == func
        assert name in action_manager._internal_action_metadata
        metadata = action_manager._internal_action_metadata[name]
        assert isinstance(metadata, FunctionMetadata)
        assert metadata.name == name
        assert metadata.description == desc
        assert metadata.is_async is False
        assert "name" in metadata.parameters["properties"]
        assert "age" in metadata.parameters["properties"]
        assert metadata.parameters["required"] == ["name"]

    def test_register_action_uses_docstring(self, action_manager: InternalActionManager):
        name = "test_sync"
        func = sync_action_simple
        action_manager.register_action(name, func) # No explicit description

        metadata = action_manager.get_action_metadata(name)
        assert metadata.description == "Simple synchronous action." # First line of docstring

    def test_register_action_no_docstring_default_desc(self, action_manager: InternalActionManager):
        name = "test_no_doc"
        func = action_no_docstring
        action_manager.register_action(name, func)

        metadata = action_manager.get_action_metadata(name)
        assert metadata.description == f"Execute the {name} action"

    def test_register_action_duplicate(self, action_manager: InternalActionManager):
        action_manager.register_action("duplicate_action", sync_action_simple)
        with pytest.raises(ValueError, match="already registered"):
            action_manager.register_action("duplicate_action", action_no_docstring)

    def test_register_action_metadata_extraction_failure(self, action_manager: InternalActionManager):
        # Mock _extract_function_metadata to raise an error
        with patch.object(action_manager, '_extract_function_metadata', side_effect=Exception("Metadata extraction failed")):
            with pytest.raises(Exception, match="Metadata extraction failed"):
                action_manager.register_action("fail_meta", sync_action_simple)
            # Ensure action was not registered
            assert "fail_meta" not in action_manager._internal_actions
            assert "fail_meta" not in action_manager._internal_action_metadata

    def test_clear_actions(self, action_manager: InternalActionManager):
        action_manager.register_action("action1", sync_action_simple)
        action_manager.register_action("action2", async_action_complex)
        assert len(action_manager._internal_actions) == 2
        assert len(action_manager._internal_action_metadata) == 2

        action_manager.clear_actions()
        assert len(action_manager._internal_actions) == 0
        assert len(action_manager._internal_action_metadata) == 0

    def test_register_actions(self, action_manager: InternalActionManager):
        functions = {
            "sync_1": sync_action_simple,
            "async_1": async_action_complex,
            "no_doc_1": action_no_docstring
        }
        action_manager.register_actions(functions)

        assert len(action_manager._internal_actions) == 3
        assert len(action_manager._internal_action_metadata) == 3
        assert "sync_1" in action_manager._internal_actions
        assert "async_1" in action_manager._internal_action_metadata
        assert action_manager.get_action_metadata("sync_1").description == "Simple synchronous action."
        assert action_manager.get_action_metadata("async_1").is_async is True
        assert action_manager.get_action_metadata("no_doc_1").description == "Execute the no_doc_1 action"

    def test_get_action_metadata(self, action_manager: InternalActionManager):
        action_manager.register_action("test_get", sync_action_simple)
        metadata = action_manager.get_action_metadata("test_get")
        assert isinstance(metadata, FunctionMetadata)
        assert metadata.name == "test_get"
        assert action_manager.get_action_metadata("non_existent") is None

    def test_get_action_function(self, action_manager: InternalActionManager):
        action_manager.register_action("test_get_func", sync_action_simple)
        func = action_manager.get_action_function("test_get_func")
        assert func == sync_action_simple
        assert action_manager.get_action_function("non_existent") is None

    def test_get_all_actions(self, action_manager: InternalActionManager):
        assert action_manager.get_all_actions() == []
        action_manager.register_action("action1", sync_action_simple)
        action_manager.register_action("action2", async_action_complex)
        assert sorted(action_manager.get_all_actions()) == sorted(["action1", "action2"])

    def test_has_action(self, action_manager: InternalActionManager):
        assert action_manager.has_action("test_has") is False
        action_manager.register_action("test_has", sync_action_simple)
        assert action_manager.has_action("test_has") is True

    def test_get_tool_definitions_none_or_all(self, action_manager: InternalActionManager):
        action_manager.register_action("action1", sync_action_simple)
        action_manager.register_action("action2", async_action_complex)

        tools_none = action_manager.get_tool_definitions() # Defaults to all
        tools_all = action_manager.get_tool_definitions("all")

        assert len(tools_none) == 2
        assert len(tools_all) == 2
        assert {t["function"]["name"] for t in tools_none} == {"action1", "action2"}
        assert {t["function"]["name"] for t in tools_all} == {"action1", "action2"}

        tool1 = next(t for t in tools_all if t["function"]["name"] == "action1")
        assert tool1["type"] == "function"
        assert tool1["function"]["description"] == "Simple synchronous action."
        assert "name" in tool1["function"]["parameters"]["properties"]

    def test_get_tool_definitions_list(self, action_manager: InternalActionManager):
        action_manager.register_action("action1", sync_action_simple)
        action_manager.register_action("action2", async_action_complex)
        action_manager.register_action("action3", action_no_docstring)

        tools = action_manager.get_tool_definitions(["action1", "action3", "non_existent"])
        assert len(tools) == 2 # non_existent is ignored
        assert {t["function"]["name"] for t in tools} == {"action1", "action3"}

    def test_get_tool_definitions_empty_list(self, action_manager: InternalActionManager):
        action_manager.register_action("action1", sync_action_simple)
        tools = action_manager.get_tool_definitions([])
        assert tools == []

    def test_get_tool_definitions_string_none(self, action_manager: InternalActionManager):
        action_manager.register_action("action1", sync_action_simple)
        tools = action_manager.get_tool_definitions("none")
        assert tools == []

    @pytest.mark.asyncio
    async def test_execute_action_sync_success(self, action_manager: InternalActionManager):
        action_manager.register_action("test_exec_sync", sync_action_simple)
        params = {"name": "Tester", "age": 42}
        result = await action_manager.execute_action("test_exec_sync", params)
        assert result == "Hello Tester, age 42"

    @pytest.mark.asyncio
    async def test_execute_action_async_success(self, action_manager: InternalActionManager):
        action_manager.register_action("test_exec_async", async_action_complex)
        params = {"items": [{"id": 1}, {"id": 2}], "config": {"bonus": 3}}
        result = await action_manager.execute_action("test_exec_async", params)
        assert result == 5 # 2 items + 3 bonus

    @pytest.mark.asyncio
    async def test_execute_action_not_found(self, action_manager: InternalActionManager):
        with pytest.raises(ValueError, match="Custom action 'non_existent' not found"):
            await action_manager.execute_action("non_existent", {})

    @pytest.mark.asyncio
    async def test_execute_action_raises_exception(self, action_manager: InternalActionManager):
        def failing_action(): raise RuntimeError("Something failed")
        action_manager.register_action("test_fail", failing_action)
        with pytest.raises(RuntimeError, match="Something failed"):
            await action_manager.execute_action("test_fail", {})

    # --- Metadata Extraction Tests ---

    def test_extract_metadata_basic(self, action_manager: InternalActionManager):
        metadata = action_manager._extract_function_metadata(sync_action_simple, "sync_simple")
        assert metadata.name == "sync_simple"
        assert metadata.description == "Simple synchronous action."
        assert metadata.is_async is False
        assert metadata.parameters == {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
                "age": {"type": "integer", "description": "Parameter age"}
            },
            "required": ["name"]
        }

    def test_extract_metadata_async(self, action_manager: InternalActionManager):
        metadata = action_manager._extract_function_metadata(async_action_complex, "async_complex")
        assert metadata.name == "async_complex"
        assert metadata.description == "Complex asynchronous action."
        assert metadata.is_async is True
        assert metadata.parameters["properties"]["items"]["type"] == "array"
        assert metadata.parameters["properties"]["config"]["type"] == "object"
        assert metadata.parameters["required"] == ["items"]

    def test_extract_metadata_param_docstring(self, action_manager: InternalActionManager):
        metadata = action_manager._extract_function_metadata(action_with_params_docstring, "params_doc")
        assert metadata.parameters["properties"]["value"]["description"] == "The float value to process."

    def test_type_to_json_schema_literal(self, action_manager: InternalActionManager):
        schema = action_manager._type_to_json_schema(Literal["A", "B", "C"])
        assert schema == {"type": "string", "enum": ["A", "B", "C"]}

    # Add more _type_to_json_schema tests if needed for complex cases