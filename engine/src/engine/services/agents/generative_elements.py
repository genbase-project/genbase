# engine/services/agents/generative_elements.py
from typing import Dict, List, Union, Literal

ELEMENT_TAG_STRUCTURE = """
<element format="format_type">
    Content conforming to the specified format_type
</element>
"""

# Defines the available formats and provides guidance for the LLM on their use.
# The keys are the valid values for the 'format' attribute in the <element> tag.
ELEMENTS_FORMAT_DEFINITIONS: Dict[str, str] = {
    "markdown": "Use for formatted text, lists, links, simple tables, and code blocks. Content should follow standard Markdown syntax.",
    "html": "Use for complex layouts, interactive elements (like forms, buttons - frontend must handle interactivity), specific styling, or when precise visual structure is needed. Content must be valid HTML snippet (usually within a div or similar block).",
    "mermaid": "Use for generating diagrams and flowcharts. Content must be valid Mermaid syntax (e.g., graph TD; A-->B;). See https://mermaid.js.org/syntax/flowchart.html.",
    "plantuml": "Use for generating UML diagrams. Content must be valid PlantUML syntax (e.g., @startuml\\nactor User\\nparticipant System\\nUser -> System: Request\\n@enduml). See https://plantuml.com/.",
    "chartjs": "Use for data visualizations like bar, line, pie charts. Content must be a JSON object conforming to the Chart.js configuration structure (defining type, data, options). See https://www.chartjs.org/docs/latest/configuration/.",
    "json": "Use for displaying structured data clearly in JSON format. Content must be valid JSON.",
    "xml": "Use for displaying structured data clearly in XML format. Content must be valid XML.",
    "plaintext": "Use for preformatted plain text where whitespace and line breaks are important (like code output or ASCII art), but no other formatting is needed within an element block.",
    # Add other formats here as needed, ensuring the frontend can render them.
    # Example: "latex": "Use for mathematical equations or complex scientific documents. Content must be valid LaTeX."
}

def get_element_format_documentation(requested_formats: Union[Literal["all", "none"], List[str]]) -> str:
    """
    Generates the documentation string explaining the <element> tag
    and listing the available formats for the LLM system prompt.

    Args:
        requested_formats: Specifies which formats to include documentation for.
                           Can be "all", "none", or a list of format names (strings).

    Returns:
        A formatted string describing the element usage and available formats,
        or an empty string if requested_formats is "none" or results in no valid formats.
    """
    if requested_formats == "none":
        return ""

    # Determine the list of format keys to document
    formats_to_include_keys: List[str] = []
    if requested_formats == "all":
        formats_to_include_keys = list(ELEMENTS_FORMAT_DEFINITIONS.keys())
    elif isinstance(requested_formats, list):
        formats_to_include_keys = [
            fmt for fmt in requested_formats if fmt in ELEMENTS_FORMAT_DEFINITIONS
        ]

    if not formats_to_include_keys:
        # No valid formats requested or available
        return ""

    # Build the documentation string
    docs = [
        "You can embed structured or rich content using the following XML tag structure:",
        ELEMENT_TAG_STRUCTURE.strip(),
        "\nReplace 'format_type' with one of the supported formats listed below.",
        "Place the content, strictly conforming to the chosen format's syntax, inside the tag.",
        "Use these elements to enhance clarity, present data effectively, create visualizations, or enable specific interactions when plain text is insufficient."
    ]

    docs.append("\nAvailable formats:")
    for fmt_key in sorted(formats_to_include_keys):
        docs.append(f"- **{fmt_key}**: {ELEMENTS_FORMAT_DEFINITIONS[fmt_key]}")

    return "\n".join(docs)
