from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from engine.services.storage.repository import RepoService
from engine.utils.yaml import YAMLUtils
from pydantic import BaseModel

from engine.services.execution.action import ActionError, ActionService
from engine.services.core.module import ModuleError, ModuleService, RelationType
from engine.services.storage.resource import ResourceService
from engine.utils.logging import logger


@dataclass
class ActionInfo:
    """Stores information about an action including its source"""
    module_id: str
    workflow: str
    action_path: str
    name: str
    description: Optional[str] = None
    source_module_name: Optional[str] = None  # Add this field
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ActionInfo to dictionary"""
        return {
            "module_id": self.module_id,
            "workflow": self.workflow,
            "action_path": self.action_path,
            "name": self.name,
            "description": self.description,
            "source_module_name": self.source_module_name
        }


class WorkflowStep(BaseModel):
    """Workflow step metadata"""
    path: str  # Format: "path/to/file:function_name"
    name: str
    description: Optional[str] = None

class Workflow(BaseModel):
    """Workflow metadata"""
    instruction: Optional[str] = None
    actions: List[WorkflowStep] = []  # Make actions optional with empty default

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
        repo_service: RepoService
    ):
        self.workspace_base = Path(workspace_base)
        self.module_base = Path(module_base)
        self.module_service = module_service
        self.action_service = action_service
        self.resource_service = resource_service
        self.repo_service = repo_service


    def _read_instruction_file(self, instruction_path: Path) -> str:
        """Read instruction file content"""
        try:
            if instruction_path.exists():
                with open(instruction_path, 'r') as f:
                    return f.read()
            logger.warning(f"Instruction file not found: {instruction_path}")
            return ""
        except Exception as e:
            logger.error(f"Failed to read instruction file {instruction_path}: {str(e)}")
            raise WorkflowError(f"Failed to read instruction file: {str(e)}")

    def _resolve_action_path(self, module_path: Path, action_path: str) -> tuple[Path, str, str]:
        """
        Resolve action path to actual file path and function name
        Returns: (actions_dir, file_path, function_name)
        """
        # Split into module and function parts (e.g., "prerequisites:check_node")
        module_part, function_name = action_path.split(":")
        
        # Ensure .py extension
        file_path = f"{module_part}.py"
        
        # Actions directory is under module root
        actions_dir = module_path / "actions"
        if not actions_dir.exists():
            raise WorkflowError(f"Actions directory not found: {actions_dir}")
            
        # Verify file exists
        full_path = actions_dir / file_path
        if not full_path.exists():
            raise WorkflowError(f"Action file not found: {full_path}")
            
        return actions_dir, file_path, function_name

    def get_workflow_metadata(self, module_id: str, workflow: str) -> Dict[str, Any]:
        """Get workflow metadata including instructions and steps"""
        try:
            # Get module info
            module_path = self.module_service.get_module_path(module_id)
            # Read and validate kit
            kit = YAMLUtils.read_kit(module_path)
            if not kit.get('workflows', {}).get(workflow):
                logger.error(f"Workflow '{workflow}' not found in kit.yaml")
                raise WorkflowError(f"Workflow '{workflow}' not found")

            workflow_data = kit['workflows'][workflow]
            
            # Handle instruction file separately from model validation
            instruction_file = workflow_data.get('instruction')
            instruction_content = ""
            if instruction_file:
                instruction_path = module_path / "instructions" / instruction_file
                instruction_content = self._read_instruction_file(instruction_path)
                
            try:
                # Create normalized workflow data for validation
                validated_data = {
                    "instruction": instruction_file,
                    "actions": workflow_data.get('actions', [])
                }
                workflow_model = Workflow.model_validate(validated_data)
                logger.info(f"""Workflow {workflow} validated:
                Instruction file: {instruction_file}
                Actions: {len(workflow_model.actions)}
                Content length: {len(instruction_content)}
                """)
            except Exception as e:
                logger.error(f"""Failed to validate workflow {workflow}:
                Error: {str(e)}
                Data: {workflow_data}
                """)
                raise WorkflowError(f"Invalid workflow configuration: {str(e)}")

            # Get function metadata for each step
            steps_metadata = []
            for step in workflow_model.actions:
                try:
                    # Resolve action path
                    actions_dir, file_path, function_name = self._resolve_action_path(
                        module_path, step.path
                    )

                    # Reuse action service to get function metadata
                    metadata = self.action_service.get_function_metadata(
                        folder_path=str(actions_dir),
                        file_path=file_path,
                        function_name=function_name
                    )

                    steps_metadata.append({
                        "name": step.name,
                        "description": step.description,
                        "action": step.path,
                        "metadata": metadata
                    })
                except (ActionError, WorkflowError) as e:
                    logger.error(f"Failed to get metadata for step {step.name}: {str(e)}")
                    # Add error information but continue processing other steps
                    steps_metadata.append({
                        "name": step.name,
                        "description": step.description,
                        "action": step.path,
                        "error": str(e)
                    })

            result = {
                "instructions": instruction_content,
                "actions": steps_metadata,
                "requirements": kit.get('dependencies', [])
            }
            logger.info(f"Got workflow metadata for {workflow}:\n{result}")
            return result

        except (ModuleError, WorkflowError) as e:
            raise WorkflowError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error getting workflow metadata: {str(e)}")
            raise WorkflowError(f"Failed to get workflow metadata: {str(e)}")


    def execute_workflow_step(
        self,
        module_id: str,
        workflow: str,
        action_info: ActionInfo,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a workflow action with full context."""
        try:
            # Get module info for the module that owns the action
            source_module_path = self.module_service.get_module_path(action_info.module_id)
            source_module_metadata = self.module_service.get_module_metadata(action_info.module_id)

            logger.info(f"Executing action from module {action_info.module_id} in workflow {action_info.workflow}")
            
            # Read kit from the source module
            kit = YAMLUtils.read_kit(source_module_path)
            source_workflow = action_info.workflow  # This will be 'share' for shared actions

            if not kit.get('workflows', {}).get(source_workflow):
                raise WorkflowError(
                    f"Workflow '{source_workflow}' not found in module {action_info.source_module_name or action_info.module_id}"
                )

            # Get the correct workflow data from source module
            workflow_data = kit['workflows'][source_workflow]
            
            # Handle instruction file separately from model validation
            instruction_file = workflow_data.get('instruction')
            source_info = f" from module {action_info.source_module_name}" if action_info.source_module_name else ""
            logger.info(f"""Executing action '{action_info.name}'{source_info} in workflow {source_workflow}
            Config: {workflow_data}
            """)
                
            try:
                # Create normalized workflow data for validation
                validated_data = {
                    "instruction": instruction_file,
                    "actions": workflow_data.get('actions', [])
                }
                workflow_model = Workflow.model_validate(validated_data)
            except Exception as e:
                logger.error(f"""Failed to validate workflow {source_workflow}:
                Error: {str(e)}
                Data: {workflow_data}
                """)
                raise WorkflowError(f"Invalid workflow configuration: {str(e)}")

            # Find the action in the source workflow
            action = next(
                (s for s in workflow_model.actions if s.name == action_info.name), 
                None
            )
            
            if not action:
                raise WorkflowError(
                    f"Action '{action_info.name}' not found in workflow '{source_workflow}' of module {action_info.source_module_name or action_info.module_id}"
                )

            # Resolve action path in source module
            actions_dir, file_path, function_name = self._resolve_action_path(
                source_module_path, action.path
            )

            # Get requirements from source module
            requirements = kit.get('dependencies', [])

            # Execute in the context of the source module
            result = self.action_service.execute_function(
                folder_path=str(actions_dir),
                file_path=file_path,
                function_name=function_name,
                parameters=parameters,
                requirements=requirements,
                env_vars=source_module_metadata.env_vars,
                repo_name=source_module_metadata.repo_name
            )

            return {
                "status": "success",
                "message": f"Successfully executed {action_info.name}{source_info}",
                "result": result
            }

        except (ModuleError, ActionError, WorkflowError) as e:
            raise WorkflowError(str(e))
