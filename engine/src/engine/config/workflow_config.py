from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Any

from engine.services.execution.stage_state import COMPLETE_WORKFLOW_SCHEMA, StageStateService

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
    agent_type: str  # "tasker" or "coder"
    base_instructions: str  # Default instructions always included
    prerequisites: List[str]  # Workflows that must be completed first
    default_actions: List[WorkflowAction] = field(default_factory=list)  # Default actions available to this workflow
    allow_multiple: bool = False  # Whether multiple chat sessions are allowed


class WorkflowConfigurations:
    """Central configuration for all core workflows"""
    
    @staticmethod
    def get_default_configs() -> Dict[str, WorkflowConfig]:
        """Get default configurations for all workflows"""
        return {
            "initialize": WorkflowConfig(
                workflow_type="initialize",
                agent_type="", # Will be overridden by kit.yaml
                base_instructions="""Initialize the module and verify all requirements are met.
                Follow these steps:
                1. Verify environment setup
                2. Install dependencies
                3. Validate initial configuration""",
                prerequisites=[],
                allow_multiple=False
            ),
            
            "maintain": WorkflowConfig(
                workflow_type="maintain",
                agent_type="", # Will be overridden by kit.yaml
                base_instructions="""Monitor and maintain the module's operation.
                Keep the module healthy and running smoothly.""",
                prerequisites=["initialize"],
                allow_multiple=True
            ),
            
            "remove": WorkflowConfig(
                workflow_type="remove",
                agent_type="", # Will be overridden by kit.yaml
                base_instructions="""Safely remove the module and clean up resources.
                Ensure all dependencies and resources are properly handled.""",
                prerequisites=["initialize"],
                allow_multiple=False
            ),
            
            "edit": WorkflowConfig(
                workflow_type="edit",
                agent_type="", # Will be overridden by kit.yaml
                base_instructions="""Make code edits with minimal impact.
                Always explain changes and ensure stability.""",
                prerequisites=["initialize"],
                allow_multiple=True
            )
        }
    @staticmethod
    def get_default_actions(stage_state_service: StageStateService) -> Dict[str, List[WorkflowAction]]:
        return {
            "initialize": [
                WorkflowAction(
                    name="complete_workflow",
                    description="Mark the current workflow as completed",
                    schema=COMPLETE_WORKFLOW_SCHEMA,
                    function=stage_state_service.complete_workflow
                )
            ],
            "remove": [
                WorkflowAction(
                    name="complete_workflow",
                    description="Mark the current workflow as completed",
                    schema=COMPLETE_WORKFLOW_SCHEMA,
                    function=stage_state_service.complete_workflow
                )
            ]
    }

    
class WorkflowConfigService:
    """Service for managing workflow configurations"""
    
    def __init__(self):
        self.default_configs = WorkflowConfigurations.get_default_configs()
        stage_state_service = StageStateService()
        self.default_actions: Dict[str, List[WorkflowAction]] = WorkflowConfigurations.get_default_actions(stage_state_service)
    
    def get_workflow_config(
        self, 
        workflow_type: str,
        kit_config: Optional[Dict] = None
    ) -> WorkflowConfig:
        """Get workflow configuration from defaults and kit.yaml"""
        if workflow_type not in self.default_configs:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
            
        base_config = self.default_configs[workflow_type]
        default_actions = self.default_actions.get(workflow_type, [])

        # Start with base config
        config = WorkflowConfig(
            workflow_type=workflow_type,
            agent_type=base_config.agent_type,
            base_instructions=base_config.base_instructions,
            prerequisites=base_config.prerequisites.copy(),
            default_actions=default_actions,
            allow_multiple=base_config.allow_multiple
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


    def can_execute_workflow(
        self,
        workflow_type: str,
        completed_workflows: Set[str]
    ) -> bool:
        """Check if a workflow can be executed based on prerequisites"""
        if workflow_type not in self.default_configs:
            return False
            
        config = self.default_configs[workflow_type]
        return all(prereq in completed_workflows for prereq in config.prerequisites)
