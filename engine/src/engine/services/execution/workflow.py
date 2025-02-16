from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, NotRequired

import yaml
import os
from engine.services.storage.repository import RepoService
from engine.utils.yaml import YAMLUtils
from pydantic import BaseModel
from engine.services.core.kit import KitConfig, KitService

from engine.services.execution.action import ActionError, ActionService, FunctionMetadata
from engine.services.core.module import ModuleError, ModuleService, RelationType
from engine.services.storage.resource import ResourceService
from loguru import logger
from engine.services.core.kit import WorkflowAction

class EnhancedWorkflowAction(BaseModel):
    """Enhanced workflow action that wraps WorkflowAction with additional metadata"""
    action: WorkflowAction
    module_id: str
    workflow: Optional[str] = None  # Workflow name if part of workflow
    metadata: Optional[FunctionMetadata] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        action_dict = self.action.to_dict()
        return {
            "action":action_dict,
            "module_id": self.module_id,
            "workflow": self.workflow,
            "metadata": self.metadata.dict() if self.metadata else None,
            "error": self.error
        }

class WorkflowMetadataResult(BaseModel):
    """Pydantic model for complete workflow metadata response"""
    instructions: str
    actions: List[EnhancedWorkflowAction]
    requirements: List[str]

@dataclass
class ActionInfo:
    """Stores information about an action"""
    module_id: str
    workflow: str
    name: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ActionInfo to dictionary"""
        return {
            "module_id": self.module_id,
            "workflow": self.workflow,
            "action_path": self.action_path,
            "name": self.name,
            "description": self.description
        }



class Workflow(BaseModel):
    """Workflow metadata"""
    instruction: Optional[str] = None
    actions: List[WorkflowAction] = []  # Make actions optional with empty default

class WorkflowExecutionResult(BaseModel):
    """Pydantic model for workflow execution result"""
    status: str
    message: str 
    result: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "status": self.status,
            "message": self.message,
            "result": self.result
        }

class WorkflowError(Exception):
    """Base exception for workflow actions"""
    pass

class WorkflowService:
    """Service for managing module workflows"""

    def __init__(
        self,
        workspace_base: str | Path,
        module_base: str | Path,
        module_service: ModuleService,
        action_service: ActionService,
        resource_service: ResourceService,
        repo_service: RepoService,
        kit_service: KitService
    ):
        self.workspace_base = Path(workspace_base)
        self.module_base = Path(module_base)
        self.module_service = module_service
        self.action_service = action_service
        self.resource_service = resource_service
        self.repo_service = repo_service
        self.kit_service = kit_service



    def get_workflow_metadata(self, module_id: str, workflow: str) -> WorkflowMetadataResult:
        """Get workflow metadata including instructions and steps"""
        try:
            # Get kit config which has all paths resolved and content loaded
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            if workflow not in kit_config.workflows:
                logger.error(f"Workflow '{workflow}' not found in kit config")
                raise WorkflowError(f"Workflow '{workflow}' not found")

            workflow_data = kit_config.workflows[workflow]
            
            # Get function metadata for each action
            steps_metadata: List[EnhancedWorkflowAction] = []
            for action in workflow_data.actions:
                try:
                    # Extract file info from pre-resolved paths
                    actions_dir = str(Path(action.full_file_path).parent)
                    file_path = Path(action.full_file_path).name
                    
                    # Get function metadata
                    metadata: FunctionMetadata = self.action_service.get_function_metadata(
                        folder_path=actions_dir,
                        file_path=file_path,
                        function_name=action.function_name
                    )
                    steps_metadata.append(EnhancedWorkflowAction(
                        action=action,
                        module_id=module_id,
                        workflow=workflow,
                        metadata=metadata
                    ))


                except (ActionError, WorkflowError) as e:
                    logger.error(f"Failed to get metadata for action {action.name}: {str(e)}")
                    # Add error information but continue processing other actions
               

            result = WorkflowMetadataResult(
                instructions=workflow_data.instruction_content,
                actions=steps_metadata,
                requirements=kit_config.dependencies
            )
            logger.info(f"Got workflow metadata for {workflow}:\n{result}")
            return result

        except (ModuleError, WorkflowError) as e:
            raise WorkflowError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error getting workflow metadata: {str(e)}")
            raise WorkflowError(f"Failed to get workflow metadata: {str(e)}")


    def get_shared_actions_metadata(self, module_id: str) -> WorkflowMetadataResult:
        """Get metadata for all shared actions from this module and context modules"""
        try:
            # Get all modules with CONTEXT relation (including this module)
            context_modules = self.module_service.get_linked_modules(
                module_id=module_id,
                relation_type=RelationType.CONTEXT
            )

            steps_metadata: List[EnhancedWorkflowAction] = []
            all_requirements = set()

            for module in context_modules:
                try:
                    # Get kit config for module
                    kit_config = self.module_service.get_module_kit_config(module.module_id)
                    
                    # Add any requirements
                    all_requirements.update(kit_config.dependencies)

                    # Get actions from this module
                    for action in kit_config.shared_actions:
                        try:
                            # Extract file info from paths
                            actions_dir = self.kit_service.get_kit_path(module.module_id) / "actions"
                            file_path = str(Path(action.path))

                            # Get function metadata
                            metadata = self.action_service.get_function_metadata(
                                folder_path=actions_dir,
                                file_path=file_path,
                                function_name=action.function_name
                            )

                            steps_metadata.append(EnhancedWorkflowAction(
                                action=action,
                                module_id=module.module_id,
                                workflow=None,  # Shared actions don't belong to a workflow
                                metadata=metadata
                            ))
                        except (ActionError, WorkflowError) as e:
                            logger.error(f"Failed to get metadata for shared action {action.name} in module {module.module_id}: {str(e)}")

                except Exception as e:
                    logger.error(f"Failed to process shared actions for module {module.module_id}: {str(e)}")
                    continue

            return WorkflowMetadataResult(
                instructions="",  # Shared actions don't have instructions
                actions=steps_metadata,
                requirements=list(all_requirements)  # Convert set back to list
            )

        except (ModuleError, WorkflowError) as e:
            raise WorkflowError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error getting shared actions metadata: {str(e)}")
            raise WorkflowError(f"Failed to get shared actions metadata: {str(e)}")

    def execute_shared_action(
        self,
        module_id: str,
        action_info: ActionInfo,
        parameters: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute a shared action from any accessible module"""
        try:
            # Get target module metadata
            target_module = self.module_service.get_module_metadata(action_info.module_id)

            # Get kit config for target module
            kit_config = self.module_service.get_module_kit_config(action_info.module_id)
            
            # Verify action exists
            action = next(
                (a for a in kit_config.shared_actions if a.name == action_info.name),
                None
            )
            if not action:
                raise WorkflowError(f"Shared action '{action_info.name}' not found")

            # Get action path info
            actions_dir = self.kit_service.get_kit_path(action_info.module_id) / "actions"
            file_path = str(Path(action.path))

            # Execute function using module context
            result = self.action_service.execute_function(
                folder_path=str(actions_dir),
                file_path=file_path,
                function_name=action.function_name,
                parameters=parameters,
                requirements=kit_config.dependencies,
                env_vars=target_module.env_vars,
                repo_name=target_module.repo_name
            )

            return WorkflowExecutionResult(
                status="success",
                message=f"Successfully executed shared action {action_info.name} from module {action_info.module_id}",
                result=result
            )

        except (ModuleError, ActionError, WorkflowError) as e:
            raise WorkflowError(str(e))

    def execute_workflow_action(
        self,
        action_info: ActionInfo,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a workflow action with full context."""
        try:
            module_path = self.module_service.get_module_path(action_info.module_id)
            # Get kit config which has all paths resolved
            kit_config = self.module_service.get_module_kit_config(action_info.module_id)
            module_metadata = self.module_service.get_module_metadata(action_info.module_id)

            logger.info(f"Executing action {action_info.name} in workflow {action_info.workflow}")
            
            if action_info.workflow not in kit_config.workflows:
                raise WorkflowError(f"Workflow '{action_info.workflow}' not found")

            workflow_data = kit_config.workflows[action_info.workflow]
            logger.info(f"""Executing action '{action_info.name}' in workflow {action_info.workflow}
            Config: {workflow_data}
            """)

            # Find the action in workflow
            action = next(
                (a for a in workflow_data.actions if a.name == action_info.name), 
                None
            )
            
            if not action:
                raise WorkflowError(
                    f"Action '{action_info.name}' not found in workflow '{action_info.workflow}'"
                )

            # Extract file info from pre-resolved paths
            actions_dir = str(module_path / "actions")
            file_path = str(Path(action.path.split(":")[0]+".py"))

            logger.info(f"Folder Path: {actions_dir}, File Path: {file_path}, Function Name: {action.function_name}, Parameters: {parameters}, Requirements: {kit_config.dependencies}, Env Vars: {module_metadata.env_vars}, Repo Name: {module_metadata.repo_name}")

            # Execute function using resolved paths
            result = self.action_service.execute_function(
                folder_path=actions_dir,
                file_path=file_path,
                function_name=action.function_name,
                parameters=parameters,
                requirements=kit_config.dependencies,
                env_vars=module_metadata.env_vars,
                repo_name=module_metadata.repo_name
            )

            return result

        except (ModuleError, ActionError, WorkflowError) as e:
            raise WorkflowError(str(e))
