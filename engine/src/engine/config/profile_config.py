from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Any

from engine.services.execution.state import StateService

@dataclass
class ProfileAction:
    """Action configuration for a profile"""
    name: str
    description: str
    schema: Dict[str, Any]
    function: Callable[..., Any]

@dataclass
class ProfileConfig:
    """Complete configuration for a profile"""
    profile_type: str
    agent_type: str  # "tasker"
    base_instructions: str  # Default instructions always included
    default_actions: List[ProfileAction] = field(default_factory=list)  # Default actions available to this profile
    allow_multiple: bool = False  # Whether multiple chat sessions are allowed


class ProfileConfigurations:
    """Central configuration for all core profiles"""
    

    
class ProfileConfigService:
    """Service for managing profile configurations"""
    
    def __init__(self):
        pass
        
    def get_profile_config(
        self, 
        profile_type: str,
        kit_config: Optional[Dict] = None
    ) -> ProfileConfig:
        """Get Profile configuration from defaults and kit.yaml"""

            

        # Start with base config
        config = ProfileConfig(
            profile_type=profile_type,
            agent_type='',
            base_instructions='',
            default_actions=[],
            allow_multiple=True
        )
        
        if kit_config:
            # Update from kit.yaml
            if "profiles" in kit_config:
                profile_config = kit_config["profiles"].get(profile_type, {})
                
                # Get profile-specific agent
                agent = profile_config.get("agent")
                if not agent:
                    # Try default agent from profiles root
                    agent = kit_config["profiles"].get("agent")
                    
                if agent:
                    # Validate agent exists in kit config
                    if agent not in {a["name"] for a in kit_config.get("agents", [])}:
                        raise ValueError(f"Agent '{agent}' not found in kit.yaml agents")
                    config.agent_type = agent
                
                # Merge instructions
                if "instruction" in profile_config:
                    config.base_instructions = f"{config.base_instructions}\n\n{profile_config['instruction']}"
                    
                # Allow profile-specific multiple sessions
                if "allow_multiple" in profile_config:
                    config.allow_multiple = profile_config["allow_multiple"]
            
        return config

