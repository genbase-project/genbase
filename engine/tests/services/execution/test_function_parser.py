# tests/services/execution/test_function_parser.py

import pytest
import ast
import textwrap # Import textwrap
from typing import List, Dict, Any, Optional, Union, Tuple

from engine.services.execution.function_parser import FunctionParser, FunctionMetadata

# --- Test Cases ---

class TestFunctionParser:

    def _parse_function(self, code: str, function_name: str) -> FunctionMetadata:
        tree = ast.parse(textwrap.dedent(code)) # Dedent the input code as well
        parser = FunctionParser(function_name)
        parser.visit(tree)
        if not parser.found:
            raise ValueError(f"Function '{function_name}' not found in code.")
        return FunctionMetadata(
            name=function_name,
            description=parser.description,
            parameters=parser.parameters,
            is_async=parser.is_async
        )

    def test_simple_function(self):
        code = """
            def simple_func(name: str, age: int = 30):
                '''This is a simple function.'''
                pass
        """
        func_name = "simple_func"
        metadata = self._parse_function(code, func_name)

        expected_description = """This is a simple function."""

        assert metadata.name == func_name
        # FIX: Use textwrap.dedent on both strings for comparison
        assert textwrap.dedent(metadata.description) == textwrap.dedent(expected_description)
        assert metadata.is_async is False
        assert metadata.parameters == {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"],
            "additionalProperties": False
        }

    def test_async_function(self):
        code = """
            import asyncio

            async def async_func(item_id: str):
                '''An asynchronous function.'''
                await asyncio.sleep(1)
                return item_id
        """
        func_name = "async_func"
        metadata = self._parse_function(code, func_name)

        expected_description = "An asynchronous function."

        assert metadata.name == func_name
        assert textwrap.dedent(metadata.description) == textwrap.dedent(expected_description)
        assert metadata.is_async is True
        assert metadata.parameters == {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"}
            },
            "required": ["item_id"],
            "additionalProperties": False
        }

    def test_no_docstring(self):
        code = "def no_docs(x, y): pass"
        func_name = "no_docs"
        metadata = self._parse_function(code, func_name)

        assert metadata.description == ""
        assert metadata.is_async is False
        assert metadata.parameters["properties"]["x"] == {"type": "object"}
        assert metadata.parameters["properties"]["y"] == {"type": "object"}
        assert sorted(metadata.parameters["required"]) == sorted(["x", "y"])

    def test_no_parameters(self):
        code = """
            def no_params():
                '''Function without parameters.'''
                return True
        """
        func_name = "no_params"
        metadata = self._parse_function(code, func_name)

        expected_description = "Function without parameters."

        assert textwrap.dedent(metadata.description) == textwrap.dedent(expected_description)
        assert metadata.is_async is False
        assert metadata.parameters == {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }

    def test_complex_types(self):
        code = """
            from typing import List, Dict, Any, Optional, Union, Tuple

            def complex_types_func(
                names: List[str],
                config: Dict[str, Any],
                maybe_num: Optional[int],
                string_or_bool: Union[str, bool],
                coords: Tuple[float, float],
                untyped_list: list,
                untyped_dict: dict,
                any_param: Any
            ):
                '''Handles complex types.'''
                pass
        """
        func_name = "complex_types_func"
        metadata = self._parse_function(code, func_name)

        expected_description = "Handles complex types."

        assert textwrap.dedent(metadata.description) == textwrap.dedent(expected_description)
        assert metadata.is_async is False
        props = metadata.parameters["properties"]

        assert props["names"] == {"type": "array", "items": {"type": "string"}}
        assert props["config"] == {"type": "object", "additionalProperties": True}
        assert props["maybe_num"] == {"type": ["integer", "null"]}
        assert sorted(props["string_or_bool"]["type"]) == sorted(["string", "boolean"])
        assert props["coords"] == {
            "type": "array",
            "items": [{"type": "number"}, {"type": "number"}],
            "minItems": 2,
            "maxItems": 2
        }
        assert props["untyped_list"] == {"type": "array"}
        assert props["untyped_dict"] == {"type": "object"}
        assert props["any_param"] == {"type": "object"}

        expected_required = [
            "names", "config", "maybe_num", "string_or_bool", "coords",
            "untyped_list", "untyped_dict", "any_param"
        ]
        assert sorted(metadata.parameters["required"]) == sorted(expected_required)

    def test_class_method(self):
        code = """
            class MyClass:
                def my_method(self, value: str):
                    '''A method in a class.'''
                    pass
        """
        func_name = "my_method"
        metadata = self._parse_function(code, func_name)

        expected_description = "A method in a class."

        assert textwrap.dedent(metadata.description) == textwrap.dedent(expected_description)
        assert metadata.is_async is False
        assert "self" not in metadata.parameters["properties"]
        assert metadata.parameters["properties"]["value"] == {"type": "string"}
        assert metadata.parameters["required"] == ["value"]

    def test_function_not_found(self):
        code = "def another_func(): pass"
        parser = FunctionParser("non_existent_func")
        tree = ast.parse(code)
        parser.visit(tree)
        assert parser.found is False

    def test_metadata_to_dict(self):
        metadata = FunctionMetadata(
            name="test",
            description="desc",
            parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
            is_async=True
        )
        expected_dict = {
            "name": "test",
            "description": "desc",
            "parameters": {"type": "object", "properties": {"x": {"type": "integer"}}},
            "is_async": True
        }
        assert metadata.to_dict() == expected_dict