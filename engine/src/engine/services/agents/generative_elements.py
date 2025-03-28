from dataclasses import dataclass
from typing import Any, Dict



@dataclass
class ElementDefinition:
    format: str
    use: str


ELEMENTS_DEFINITIONS: Dict[str, ElementDefinition] = {
        "select": {
            "format": """
<giml>
    <select id="<unique id>">
            <item description="Description of what this option means">Option text1</item>
            <item description="Description of what this second option means">Option text2</item>
            ...
    </select>
</giml>""",
            "use": "Prompt the user with options"
        },
        "code_diff": {
            "format": """
<giml>
    <code file="path/to/file" id="<unique id>">
        <original>Original code block</original>
        <updated>Updated code block</updated>
    </code>
</giml>""",
            "use": "Show code changes with original and updated versions"
        }
    }

