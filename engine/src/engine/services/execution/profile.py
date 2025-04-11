from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, NotRequired

import yaml
import os
from engine.db.models import ProvideType
from engine.services.storage.repository import RepoService
from engine.utils.yaml import YAMLUtils
from pydantic import BaseModel
from engine.services.core.kit import InstructionItem, KitConfig, KitService

from engine.services.execution.tool import ToolError, ToolService, FunctionMetadata
from engine.services.core.module import ModuleError, ModuleService
from engine.services.storage.resource import ResourceService
from loguru import logger
from engine.services.core.kit import ProfileTool

class FullProfileTool(BaseModel):
    """Enhanced profile tool that wraps profileTool with additional metadata"""
    tool: ProfileTool
    module_id: str
    profile: Optional[str] = None  # profile name if part of profile
    metadata: Optional[FunctionMetadata] = None
    error: Optional[str] = None
    is_provided: Optional[bool] = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        tool_dict = self.tool.to_dict()
        return {
            "tool":tool_dict,
            "module_id": self.module_id,
            "profile": self.profile,
            "metadata": self.metadata.dict() if self.metadata else None,
            "error": self.error
        }

class ProfileMetadataResult(BaseModel):
    """Pydantic model for complete profile metadata response"""
    instructions: List[InstructionItem]
    tools: List[FullProfileTool]
    requirements: List[str]

@dataclass
class ToolInfo:
    """Stores information about an tool"""
    module_id: str
    name: str
    profile: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ToolInfo to dictionary"""
        return {
            "module_id": self.module_id,
            "profile": self.profile,
            "tool_path": self.tool_path,
            "name": self.name,
            "description": self.description
        }



class Profile(BaseModel):
    """profile metadata"""
    instruction: Optional[str] = None
    tool: List[ProfileTool] = []  # Make tool optional with empty default

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
    """Base exception for profile tools"""
    pass

class ProfileService:
    """Service for managing module profiles"""

    def __init__(
        self,
        workspace_base: str | Path,
        module_base: str | Path,
        module_service: ModuleService,
        tool_service: ToolService,
        resource_service: ResourceService,
        repo_service: RepoService,
        kit_service: KitService
    ):
        self.workspace_base = Path(workspace_base)
        self.module_base = Path(module_base)
        self.module_service = module_service
        self.tool_service = tool_service
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
            
            # Get function metadata for each tool
            tools_metadata: List[FullProfileTool] = []
            for tool in profile_data.tools:
                try:
                    # Parse the path to determine file path and function name
                    if ":" in tool.path:
                        # Traditional format: path:function
                        module_name, function_name = tool.path.split(":")
                        file_path = f"{module_name}.py"
                    else:
                        # New format: just function name
                        function_name = tool.path
                        file_path = "__init__.py"
                    
                    # Extract file info from pre-resolved paths
                    tools_dir = str(Path(tool.full_file_path).parent)
                    
                    # Get function metadata
                    metadata: FunctionMetadata = self.tool_service.get_function_metadata(
                        folder_path=tools_dir,
                        file_path=file_path,
                        function_name=function_name
                    )
                    tools_metadata.append(FullProfileTool(
                        tool=tool,
                        module_id=module_id,
                        profile=profile,
                        metadata=metadata
                    ))

                except (ToolError, ProfileError) as e:
                    logger.error(f"Failed to get metadata for tool {tool.name}: {str(e)}")

            instructions = profile_data.instructions
            if with_provided:
                # Get modules
                modules = self.module_service.get_modules_providing_to(module_id, ProvideType.TOOL)
                logger.info(f"Got modules providing to {module_id}: {[m.module_id for m in modules]}")
                for module in modules:

                    logger.info(f"Getting provided instructions for module {module.module_id}")

                    provided_instructions = self.resource_service.get_provided_instruction_resources(module.module_id)
                    
                    for resource in provided_instructions:
                        instructions.append(InstructionItem(
                            path=resource.path,
                            name=resource.name,
                            content=resource.content,
                            description=resource.description,
                            module_id=module.module_id,
                        ))

                    # add tools
                    kit_config = self.module_service.get_module_kit_config(module.module_id)
                    for tool in kit_config.provide.tools:
                        logger.info(f"Getting provided tool {tool.name} in module {module.module_id}")
                        try:
                            # Parse the path to determine file path and function name
                            if ":" in tool.path:
                                # Traditional format: path:function
                                module_name, function_name = tool.path.split(":")
                                file_path = f"{module_name}.py"
                            else:
                                # New format: just function name
                                function_name = tool.path
                                file_path = "__init__.py"
                            
                            # Extract file info from pre-resolved paths
                            tools_dir = self.kit_service.get_kit_path(kit_config.owner, kit_config.id, kit_config.version) / "tools"

                            # Get function metadata
                            metadata = self.tool_service.get_function_metadata(
                                folder_path=tools_dir,
                                file_path=file_path,
                                function_name=function_name
                            )

                            logger.info(f"Got metadata for provided tool {function_name} in module {module.module_id}")

                            tools_metadata.append(FullProfileTool(
                                tool=tool,
                                module_id=module.module_id,
                                profile=profile,
                                metadata=metadata,
                                is_provided=True
                            ))
                        except (ToolError, ProfileError) as e:
                            logger.error(f"Failed to get metadata for shared tool {tool.name} in module {module.module_id}: {str(e)}")

            result = ProfileMetadataResult(
                instructions=profile_data.instructions,
                tools=tools_metadata,
                requirements=kit_config.dependencies
            )
            logger.info(f"Got profile metadata for {profile}:\n{result}")
            return result

        except (ModuleError, ProfileError) as e:
            raise ProfileError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error getting profile metadata: {str(e)}")
            raise ProfileError(f"Failed to get profile metadata: {str(e)}")

    def execute_profile_tool(
        self,
        tool_info: ToolInfo,
        parameters: Dict[str, Any],
        with_provided: bool = False
    ) -> Any:
        """Execute a profile tool with full context."""
        try:
            module_path = self.module_service.get_module_path(tool_info.module_id)
            # Get kit config which has all paths resolved
            kit_config = self.module_service.get_module_kit_config(tool_info.module_id)
            module_metadata = self.module_service.get_module_metadata(tool_info.module_id)

            logger.info(f"Executing tool {tool_info.name} in profile {tool_info.profile}")
            
            if with_provided:
                # Get provided tool
                tool = next(
                    (a for a in kit_config.provide.tools if a.name == tool_info.name), 
                    None
                )
            else:
                if tool_info.profile not in kit_config.profiles:
                    raise ProfileError(f"profile '{tool_info.profile}' not found")

                profile_data = kit_config.profiles[tool_info.profile]
                logger.info(f"""Executing tool '{tool_info.name}' in profile {tool_info.profile}
                Config: {profile_data}
                """)

                # Find the tool in profile
                tool = next(
                    (a for a in profile_data.tools if a.name == tool_info.name), 
                    None
                )
            
            if not tool:
                raise ProfileError(
                    f"Tool '{tool_info.name}' not found in profile '{tool_info.profile}'"
                )

            # Extract file info
            if ":" in tool.path:
                # Traditional format: path:function
                module_name, function_name = tool.path.split(":")
                file_path = f"{module_name}.py"
            else:
                # New format: just function name
                function_name = tool.path
                file_path = "__init__.py"

            tools_dir = str(module_path / "tools")

            logger.info(f"Folder Path: {tools_dir}, File Path: {file_path}, Function Name: {function_name}, Parameters: {parameters}, Requirements: {kit_config.dependencies}, Env Vars: {module_metadata.env_vars}, Repo Name: {module_metadata.repo_name}")

            # Execute function using resolved paths
            result = self.tool_service.execute_function(
                folder_path=tools_dir,
                file_path=file_path,
                function_name=function_name,
                parameters=parameters,
                requirements=kit_config.dependencies,
                env_vars=module_metadata.env_vars,
                repo_name=module_metadata.repo_name,
                base_image=kit_config.image,
                ports=kit_config.ports,
                module_id=tool_info.module_id,
            )

            return result

        except (ModuleError, ToolError, ProfileError) as e:
            raise ProfileError(str(e))