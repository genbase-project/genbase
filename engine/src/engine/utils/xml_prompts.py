"""Utilities for generating XML-formatted prompts for agent user interactions"""

from typing import List, Optional, Tuple

def create_option(text: str, description: Optional[str] = None) -> str:
    """Create an XML option element"""
    if description:
        return f'<option description="{description}">{text}</option>'
    return f'<option>{text}</option>'

def create_user_prompt(question: str, options: List[Tuple[str, Optional[str]]] = None) -> str:
    """
    Create a complete XML user prompt with question and options
    
    Args:
        question: The question to display
        options: List of (text, description) tuples for each option
                Description is optional and can be None
    
    Returns:
        XML formatted prompt string
    """
    xml = f"<user_prompt>\n<question>{question}</question>\n"
    
    if options:
        xml += "<options>\n"
        for text, desc in options:
            xml += create_option(text, desc) + "\n"
        xml += "</options>\n"
        
    xml += "</user_prompt>"
    return xml

def create_confirmation_prompt(
    action: str,
    yes_desc: str = "Continue with the operation",
    no_desc: str = "Cancel the operation"
) -> str:
    """
    Create a standard confirmation prompt
    
    Args:
        action: The action being confirmed
        yes_desc: Description for the Yes option
        no_desc: Description for the No option
    
    Returns:
        XML formatted confirmation prompt
    """
    question = f"Would you like to {action}?"
    options = [
        ("Yes", yes_desc),
        ("No", no_desc)
    ]
    return create_user_prompt(question, options)

# Common prompts that can be reused
CONFIRM_PROCEED = create_user_prompt(
    "Would you like to proceed?",
    [
        ("Yes", "Continue with the operation"),
        ("No", "Cancel the operation")
    ]
)

CONFIRM_CHANGES = create_user_prompt(
    "Would you like me to apply these changes?",
    [
        ("Yes", "Apply the proposed changes"),
        ("No", "Cancel and make no changes")
    ]
)
