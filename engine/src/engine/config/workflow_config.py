from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Any

from engine.services.execution.state import StateService

@dataclass
class WorkflowAction:
    """Action configuration for a workflow"""
    name: str
    description: str
    schema: Dict[str, Any]
    function: Callable[..., Any]

@dataclass
class WorkflowConfig:
    """Complete configuration for a workflow"""
    workflow_type: str
    agent_type: str  # "tasker"
    base_instructions: str  # Default instructions always included
    default_actions: List[WorkflowAction] = field(default_factory=list)  # Default actions available to this workflow
    allow_multiple: bool = False  # Whether multiple chat sessions are allowed


class WorkflowConfigurations:
    """Central configuration for all core workflows"""
    

    
class WorkflowConfigService:
    """Service for managing workflow configurations"""
    
    def __init__(self):
        pass
        
    def get_workflow_config(
        self, 
        workflow_type: str,
        kit_config: Optional[Dict] = None
    ) -> WorkflowConfig:
        """Get workflow configuration from defaults and kit.yaml"""

            

        # Start with base config
        config = WorkflowConfig(
            workflow_type=workflow_type,
            agent_type='',
            base_instructions='',
            default_actions=[],
            allow_multiple=True
        )
        
        if kit_config:
            # Update from kit.yaml
            if "workflows" in kit_config:
                workflow_config = kit_config["workflows"].get(workflow_type, {})
                
                # Get workflow-specific agent
                agent = workflow_config.get("agent")
                if not agent:
                    # Try default agent from workflows root
                    agent = kit_config["workflows"].get("agent")
                    
                if agent:
                    # Validate agent exists in kit config
                    if agent not in {a["name"] for a in kit_config.get("agents", [])}:
                        raise ValueError(f"Agent '{agent}' not found in kit.yaml agents")
                    config.agent_type = agent
                
                # Merge instructions
                if "instruction" in workflow_config:
                    config.base_instructions = f"{config.base_instructions}\n\n{workflow_config['instruction']}"
                    
                # Allow workflow-specific multiple sessions
                if "allow_multiple" in workflow_config:
                    config.allow_multiple = workflow_config["allow_multiple"]
            
        return config

