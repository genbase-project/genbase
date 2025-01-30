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




class WorkflowStep(BaseModel):
    """Workflow step metadata"""
    path: str  # Format: "path/to/file:function_name"
    name: str
    description: Optional[str] = None

class Workflow(BaseModel):
    """Workflow metadata"""
    instruction: Optional[str] = None
    actions: List[WorkflowStep]

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
            return ""
        except Exception as e:
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
                raise WorkflowError(f"Workflow '{workflow}' not found")

            workflow_data = kit['workflows'][workflow]
            workflow_model = Workflow.model_validate(workflow_data)

            # Read instruction file if specified
            instruction_content = ""
            if workflow_model.instruction:
                instruction_path = module_path / "instructions" / workflow_model.instruction
                instruction_content = self._read_instruction_file(instruction_path)

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
                    # Add error information but continue processing other steps
                    steps_metadata.append({
                        "name": step.name,
                        "description": step.description,
                        "action": step.path,
                        "error": str(e)
                    })

            return {
                "instructions": instruction_content,
                "actions": steps_metadata,
                "requirements": kit.get('dependencies', [])
            }

        except (ModuleError, WorkflowError) as e:
            raise WorkflowError(str(e))


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
            workflow_model = Workflow.model_validate(workflow_data)

            source_info = f" from module {action_info.source_module_name}" if action_info.source_module_name else ""
            logger.info(f"Executing action '{action_info.name}'{source_info} in workflow {source_workflow}")

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