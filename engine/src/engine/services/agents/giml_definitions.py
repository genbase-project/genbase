from dataclasses import dataclass
from typing import Any, Dict



@dataclass
class GimlDefinition:
    format: str
    use: str
    schema: Dict[str, Any]


GIML_DEFINITIONS: Dict[str, GimlDefinition] = {
        "select": {
            "format": """
<giml>
    <select id="<unique id>">
            <item description="Description of what this option means">Option text1</item>
            <item description="Description of what this second option means">Option text2</item>
            ...
    </select>
</giml>""",
            "use": "Prompt the user with options",
            "schema": {
                "children": {
                    "select": {
                        "attributes": ["id"],
                        "children": {
                            "item": {
                                "attributes": ["description"],
                                "type": "text",
                                "multiple": True
                            }
                        }
                    }
                }
            }
        },
        "code_diff": {
            "format": """
<giml>
    <code file="path/to/file" id="<unique id>">
        <original>Original code block</original>
        <updated>Updated code block</updated>
    </code>
</giml>""",
            "use": "Show code changes with original and updated versions",
            "schema": {
                "children": {
                    "code": {
                        "attributes": ["file", "id"],
                        "children": {
                            "original": {"type": "text"},
                            "updated": {"type": "text"}
                        }
                    }
                }
            }
        }
    }

