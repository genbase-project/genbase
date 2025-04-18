import ast
import hashlib
import json
import os
import subprocess
import sys
import venv
import inspect
from pathlib import Path
from typing import Any, Dict, List, Set, Callable, Optional, Type, Union, get_args, get_origin, Literal
from types import UnionType

import cloudpickle
from pydantic import BaseModel, create_model

from engine.services.core.kit import Port
from engine.services.storage.workspace import WorkspaceService
from loguru import logger
import docker
import tempfile
from docker.errors import DockerException

class FunctionMetadata(BaseModel):
    """Function metadata in OpenAI function calling format"""
    name: str
    description: str
    parameters: Dict[str, Any]
    is_async: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format"""
        return {
            "name": self.name,
            "description": self.description, 
            "parameters": self.parameters,
            "is_async": self.is_async
        }

class FunctionParser(ast.NodeVisitor):
    """AST parser to extract function information in OpenAI schema format"""
    def __init__(self, function_name: str):
        self.function_name = function_name
        self.description = ""
        self.parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
        self.found = False
        self.is_async = False

    def _get_type_schema(self, annotation) -> Dict[str, Any]:
        """Convert Python type annotation to JSON schema"""
        if annotation is None:
            return {"type": "object"}

        if isinstance(annotation, ast.Name):
            type_map = {
                "str": {"type": "string"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "bool": {"type": "boolean"},
                "list": {"type": "array"},
                "Dict": {"type": "object"},  # Handle Dict as a name directly
                "dict": {"type": "object"},
                "Any": {"type": "object"}
            }
            return type_map.get(annotation.id, {"type": "object"})

        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == "Dict":
                    # For Dict type, we specify it's an object that can have additional properties
                    return {
                        "type": "object",
                        "additionalProperties": True
                    }
                elif annotation.value.id == "List":
                    return {
                        "type": "array",
                        "items": self._get_type_schema(annotation.slice)
                    }
                elif annotation.value.id == "Tuple":
                    # For tuples, represent as array with fixed items
                    if isinstance(annotation.slice, ast.Tuple):
                        return {
                            "type": "array",
                            "items": [self._get_type_schema(item) for item in annotation.slice.elts],
                            "minItems": len(annotation.slice.elts),
                            "maxItems": len(annotation.slice.elts)
                        }
                    else:
                        return {"type": "array"}
                elif annotation.value.id == "Optional":
                    type_schema = self._get_type_schema(annotation.slice)
                    if isinstance(type_schema["type"], list):
                        if "null" not in type_schema["type"]:
                            type_schema["type"].append("null")
                    else:
                        type_schema["type"] = [type_schema["type"], "null"]
                    return type_schema
                elif annotation.value.id == "Union":
                    if isinstance(annotation.slice, ast.Tuple):
                        types = []
                        for elt in annotation.slice.elts:
                            type_schema = self._get_type_schema(elt)
                            if "type" in type_schema:
                                if isinstance(type_schema["type"], list):
                                    types.extend(type_schema["type"])
                                else:
                                    types.append(type_schema["type"])
                        return {"type": list(set(types))} if types else {"type": "object"}
        
        # Default fallback
        return {"type": "object"}
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit a function definition"""
        if node.name == self.function_name:
            self.found = True
            
            # Get docstring
            docstring = ast.get_docstring(node)
            self.description = docstring or ""
            
            # Process parameters
            for arg in node.args.args:
                if arg.arg == 'self':  # Skip self parameter
                    continue
                    
                # Get type annotation if available
                annotation = arg.annotation
                param_schema = self._get_type_schema(annotation)
                
                # Add description from docstring
                if docstring:
                    param_docs = [
                        line.strip()
                        for line in docstring.split("\n")
                        if f":param {arg.arg}:" in line
                    ]
                    if param_docs:
                        param_desc = param_docs[0].split(":", 2)[-1].strip()
                        param_schema["description"] = param_desc

                self.parameters["properties"][arg.arg] = param_schema
                
                # If no default value, parameter is required
                defaults_offset = len(node.args.defaults)
                args_offset = len(node.args.args) - defaults_offset
                if node.args.args.index(arg) < args_offset:
                    self.parameters["required"].append(arg.arg)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit an async function definition"""
        self.is_async = True
        self.visit_FunctionDef(node)
