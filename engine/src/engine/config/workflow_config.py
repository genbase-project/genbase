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
    
    TASKER_AGENT = "tasker"
    CODER_AGENT = "coder"
    
 
    @staticmethod
    def get_default_configs() -> Dict[str, WorkflowConfig]:
        """Get default configurations for all workflows"""
        return {
            "initialize": WorkflowConfig(
                workflow_type="initialize",
                agent_type=WorkflowConfigurations.TASKER_AGENT,
                base_instructions="""You are an initialization agent responsible for setting up the module.
                Verify all requirements are met before completion.
                Follow these steps:
                1. Verify environment setup
                2. Install dependencies
                3. Validate initial configuration""",
                prerequisites=[],
                allow_multiple=False
            ),
            
            "maintain": WorkflowConfig(
                workflow_type="maintain",
                agent_type=WorkflowConfigurations.TASKER_AGENT,
                base_instructions="""You are a maintenance agent responsible for keeping the module healthy.
                Monitor and maintain the module's operation.""",
                prerequisites=["initialize"],
                allow_multiple=True
            ),
            
            "remove": WorkflowConfig(
                workflow_type="remove",
                agent_type=WorkflowConfigurations.TASKER_AGENT,
                base_instructions="""You are responsible for safely removing the module.
                Ensure all resources are cleaned up and dependencies are handled.""",
                prerequisites=["initialize"],
                allow_multiple=False
            ),
            
            "edit": WorkflowConfig(
                workflow_type="edit",
                agent_type=WorkflowConfigurations.CODER_AGENT,
                base_instructions="""You are a code editing agent.
                Make careful and minimal necessary changes.
                Always explain changes and wait for confirmation.""",
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
        """Get workflow configuration, optionally merged with kit.yaml config"""
        if workflow_type not in self.default_configs:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
            
        base_config = self.default_configs[workflow_type]
        default_actions = self.default_actions.get(workflow_type, [])
        
        if not kit_config:
            config = WorkflowConfig(
                workflow_type=workflow_type,  # Use passed in type, not base type
                agent_type=base_config.agent_type,
                base_instructions=base_config.base_instructions,
                prerequisites=base_config.prerequisites.copy(),
                default_actions=default_actions,
                allow_multiple=base_config.allow_multiple  # Pass through allow_multiple setting
            )
        else:
            # Create copy of base config with kit customizations
            config = WorkflowConfig(
                workflow_type=workflow_type,  # Use passed in type, not base type
                agent_type=base_config.agent_type,
                base_instructions=f"{base_config.base_instructions}\n\n{kit_config.get('instruction', '')}",
                prerequisites=base_config.prerequisites.copy(),
                default_actions=default_actions,
                allow_multiple=kit_config.get('allow_multiple', base_config.allow_multiple)  # Allow override from kit config
            )
            
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
