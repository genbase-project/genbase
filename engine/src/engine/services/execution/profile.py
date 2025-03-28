from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, NotRequired

import yaml
import os
from engine.db.models import ProvideType
from engine.services.storage.repository import RepoService
from engine.utils.yaml import YAMLUtils
from pydantic import BaseModel
from engine.services.core.kit import KitConfig, KitService

from engine.services.execution.action import ActionError, ActionService, FunctionMetadata
from engine.services.core.module import ModuleError, ModuleService, RelationType
from engine.services.storage.resource import ResourceService
from loguru import logger
from engine.services.core.kit import ProfileAction

class FullProfileAction(BaseModel):
    """Enhanced profile action that wraps profileAction with additional metadata"""
    action: ProfileAction
    module_id: str
    profile: Optional[str] = None  # profile name if part of profile
    metadata: Optional[FunctionMetadata] = None
    error: Optional[str] = None
    is_provided: Optional[bool] = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        action_dict = self.action.to_dict()
        return {
            "action":action_dict,
            "module_id": self.module_id,
            "profile": self.profile,
            "metadata": self.metadata.dict() if self.metadata else None,
            "error": self.error
        }

class ProfileMetadataResult(BaseModel):
    """Pydantic model for complete profile metadata response"""
    instructions: str
    actions: List[FullProfileAction]
    requirements: List[str]

@dataclass
class ActionInfo:
    """Stores information about an action"""
    module_id: str
    name: str
    profile: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ActionInfo to dictionary"""
        return {
            "module_id": self.module_id,
            "profile": self.profile,
            "action_path": self.action_path,
            "name": self.name,
            "description": self.description
        }



class Profile(BaseModel):
    """profile metadata"""
    instruction: Optional[str] = None
    actions: List[ProfileAction] = []  # Make actions optional with empty default

class ProfileExecutionResult(BaseModel):
    """Pydantic model for profile execution result"""
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

class ProfileError(Exception):
    """Base exception for profile actions"""
    pass

class ProfileService:
    """Service for managing module profiles"""

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



    def get_profile_metadata(self, module_id: str, profile: str, with_provided: bool = False) -> ProfileMetadataResult:
        """Get profile metadata including instructions and steps"""
        try:
            # Get kit config which has all paths resolved and content loaded
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            if profile not in kit_config.profiles:
                logger.error(f"profile '{profile}' not found in kit config")
                raise ProfileError(f"profile '{profile}' not found")

            profile_data = kit_config.profiles[profile]
            
            # Get function metadata for each action
            actions_metadata: List[FullProfileAction] = []
            for action in profile_data.actions:
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
                    actions_metadata.append(FullProfileAction(
                        action=action,
                        module_id=module_id,
                        profile=profile,
                        metadata=metadata
                    ))


                except (ActionError, ProfileError) as e:
                    logger.error(f"Failed to get metadata for action {action.name}: {str(e)}")
                    # Add error information but continue processing other actions
            final_instructions = profile_data.instruction_content

            if with_provided:
                # Get modules
                modules = self.module_service.get_modules_providing_to(module_id, ProvideType.ACTION)
                logger.info(f"Got modules providing to {module_id}: {[m.module_id for m in modules]}")
                for module in modules:

                    logger.info(f"Getting provided instructions for module {module.module_id}")

                    provided_instructions = self.resource_service.get_provided_instruction_resources(module.module_id)
                    final_instructions += "\n\nProvided Instructions from Module: " + module.module_id + "\n"
                    for resource in provided_instructions:
                        final_instructions += f"\n\n{resource.content}"



                    # add actions
                    kit_config = self.module_service.get_module_kit_config(module.module_id)
                    for action in kit_config.provide.actions:
                        logger.info(f"Getting provided action {action.name} in module {module.module_id}")
                        try:
                            # Extract file info from pre-resolved paths
                            actions_dir = self.kit_service.get_kit_path(kit_config.owner, kit_config.id, kit_config.version) / "actions"
                            file_path = str(Path(action.path.split(":")[0]+".py"))

                            # Get function metadata
                            metadata = self.action_service.get_function_metadata(
                                folder_path=actions_dir,
                                file_path=file_path,
                                function_name=action.function_name
                            )

                            logger.info(f"Got metadata for provided action {action.function_name} in module {module.module_id}")

                            actions_metadata.append(FullProfileAction(
                                action=action,
                                module_id=module.module_id,
                                profile=profile,
                                metadata=metadata,
                                is_provided=True
                            ))
                        except (ActionError, ProfileError) as e:
                            logger.error(f"Failed to get metadata for shared action {action.name} in module {module.module_id}: {str(e)}")



            result = ProfileMetadataResult(
                instructions=profile_data.instruction_content,
                actions=actions_metadata,
                requirements=kit_config.dependencies
            )
            logger.info(f"Got profile metadata for {profile}:\n{result}")
            return result

        except (ModuleError, ProfileError) as e:
            raise ProfileError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error getting profile metadata: {str(e)}")
            raise ProfileError(f"Failed to get profile metadata: {str(e)}")


    def execute_profile_action(
        self,
        action_info: ActionInfo,
        parameters: Dict[str, Any],
        with_provided: bool = False
    ) -> Any:
        """Execute a profile action with full context."""
        try:
            module_path = self.module_service.get_module_path(action_info.module_id)
            # Get kit config which has all paths resolved
            kit_config = self.module_service.get_module_kit_config(action_info.module_id)
            module_metadata = self.module_service.get_module_metadata(action_info.module_id)

            logger.info(f"Executing action {action_info.name} in profile {action_info.profile}")
            
            if with_provided:
                # Get provided action
                action = next(
                    (a for a in kit_config.provide.actions if a.name == action_info.name), 
                    None
                )
            else:

                if action_info.profile not in kit_config.profiles:
                    raise ProfileError(f"profile '{action_info.profile}' not found")

                profile_data = kit_config.profiles[action_info.profile]
                logger.info(f"""Executing action '{action_info.name}' in profile {action_info.profile}
                Config: {profile_data}
                """)

                # Find the action in profile
                action = next(
                    (a for a in profile_data.actions if a.name == action_info.name), 
                    None
                )




            
            if not action:
                raise ProfileError(
                    f"Action '{action_info.name}' not found in profile '{action_info.profile}'"
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
                repo_name=module_metadata.repo_name,
                base_image=kit_config.image,
                ports=kit_config.ports
            )

            return result

        except (ModuleError, ActionError, ProfileError) as e:
            raise ProfileError(str(e))
