from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentContext:
    """Context for an agent operation"""
    module_id: str
    profile: str
    user_input: str
    session_id: Optional[str] = None