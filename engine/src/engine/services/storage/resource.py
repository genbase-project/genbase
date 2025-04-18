import glob
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC, timezone
import glob

import yaml
from engine.services.execution.model import ModelService
from engine.utils.file import is_safe_path
from engine.utils.yaml import YAMLUtils
from pydantic import BaseModel
from sqlalchemy.orm import Session

from engine.services.core.module import ModuleError, ModuleService
from loguru import logger
from engine.db.models import ChatHistory
from engine.db.session import get_db


class Resource(BaseModel):
    """Resource metadata"""
    path: str  # Full path including folders e.g. "folder1/folder2/file.txt"
    name: str  # Just the file name e.g. "file.txt"
    content: str
    description: Optional[str] = None

class ResourceError(Exception):
    """Base exception for resource operations"""
    pass

class ResourceService:
    """Service for managing module resources"""

    def __init__(
        self,
        module_base: str | Path,
        workspace_base: str | Path,
        module_service: ModuleService,
        model_service: ModelService
    ):
        self.module_base = Path(module_base)
        self.workspace_base = Path(workspace_base)
        self.module_service = module_service
        self.model_service = model_service
        mimetypes.init()







    def list_workspace_paths(self, module_id: str) -> List[Dict]:
        """Get metadata for all files in the workspace based on kit config."""
        try:
            module_info = self.module_service.get_module_metadata(module_id)
            module_path = self.module_service.get_module_path(module_id)
            kit = YAMLUtils.read_kit(module_path)

            file_metadata_list = []
            processed_paths = set()  # To avoid duplicates if patterns overlap

            if not kit.get('workspace', {}).get('files'):
                return []

            workspace_path = self.workspace_base / module_info.workspace_name
            if not workspace_path.exists():
                return []

            # Get ignored patterns from kit.yaml
            ignored_patterns = kit.get('workspace', {}).get('ignore', [])
            # Always ignore .git - add it explicitly
            if ".git" not in ignored_patterns:
                ignored_patterns.append(".git")

            for file_spec in kit['workspace']['files']:
                pattern = file_spec['path']
                recursive = "**" in pattern
                glob_func = workspace_path.rglob if recursive else workspace_path.glob

                for item_path in glob_func(pattern):
                    try:
                        relative_path = item_path.relative_to(workspace_path)
                        relative_path_str = relative_path.as_posix()

                        # Skip if already processed
                        if relative_path_str in processed_paths:
                            continue

                        # Check against ignore patterns - improve the matching logic
                        should_ignore = False
                        for ignore_pattern in ignored_patterns:
                            # For exact directory match (like ".git")
                            if ignore_pattern in relative_path_str.split('/'):
                                should_ignore = True
                                break
                            
                            # For glob pattern matching
                            if any(Path(part).match(ignore_pattern) for part in relative_path_str.split('/')):
                                should_ignore = True
                                break
                                
                            # Handle patterns with wildcards
                            if '*' in ignore_pattern:
                                # Convert the glob pattern to a format Path.match can use
                                # or use the fnmatch module for proper glob matching
                                import fnmatch
                                if fnmatch.fnmatch(relative_path_str, ignore_pattern):
                                    should_ignore = True
                                    break

                        if should_ignore:
                            continue

                        if item_path.is_file():
                            mime_type, _ = mimetypes.guess_type(item_path)
                            stats = item_path.stat()
                            last_modified_dt = datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc)

                            file_metadata_list.append({
                                "path": relative_path_str,
                                "name": item_path.name,
                                "mime_type": mime_type,
                                "size": stats.st_size,
                                "last_modified": last_modified_dt.isoformat()
                            })
                            processed_paths.add(relative_path_str)

                    except Exception as e:
                        logger.error(f"Failed to process path {item_path} for module {module_id}: {str(e)}")
                        continue  # Skip this file on error

            # Sort by path for consistent ordering
            file_metadata_list.sort(key=lambda x: x['path'])
            return file_metadata_list

        except (ModuleError, yaml.YAMLError) as e:
            logger.error(f"Error accessing module/kit info for {module_id}: {e}")
            raise ResourceError(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error listing workspace paths for {module_id}")
            raise ResourceError(f"Unexpected error listing workspace paths: {str(e)}")

    # --- NEW METHOD: Get Workspace File Content ---
    def get_workspace_file(self, module_id: str, relative_path: str) -> Tuple[bytes, Optional[str]]:
        """
        Gets the content (bytes) and MIME type of a specific file in the workspace.

        Args:
            module_id: The ID of the module.
            relative_path: The relative path of the file within the workspace.

        Returns:
            A tuple containing (file_content_bytes, mime_type).

        Raises:
            ResourceError: If the file is not found, not safe, or cannot be read.
        """
        try:
            module_info = self.module_service.get_module_metadata(module_id)
            workspace_path = self.workspace_base / module_info.workspace_name
            full_path = (workspace_path / relative_path).resolve()

            # Security Check: Ensure the path is within the workspace
            if not is_safe_path(workspace_path, relative_path):
                 logger.error(f"Attempt to access unsafe path: {relative_path} in module {module_id}")
                 raise ResourceError("Access denied: Invalid file path.")

            if not full_path.exists():
                raise ResourceError(f"File not found: {relative_path}")
            if not full_path.is_file():
                raise ResourceError(f"Path is not a file: {relative_path}")

            # Read file as bytes
            content_bytes = full_path.read_bytes()
            mime_type, _ = mimetypes.guess_type(full_path)

            return content_bytes, mime_type

        except (ModuleError, FileNotFoundError) as e:
            logger.error(f"File or module not found for {module_id}, path {relative_path}: {e}")
            raise ResourceError(f"Resource not found: {relative_path}")
        except PermissionError:
             logger.error(f"Permission denied reading {relative_path} in module {module_id}")
             raise ResourceError(f"Permission denied for file: {relative_path}")
        except Exception as e:
            logger.exception(f"Error getting file content for {module_id}, path {relative_path}")
            raise ResourceError(f"Failed to get file content: {str(e)}")






    def _read_file_content(self, file_path: Path) -> str:
        """Read file content safely"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ResourceError(f"Failed to read file {file_path}: {str(e)}")

    def get_workspace_resources(self, module_id: str) -> List[Resource]:
        try:
            module_info = self.module_service.get_module_metadata(module_id)
            module_path = self.module_service.get_module_path(module_id)
            logger.info(f"Getting workspace resources for module {module_info}")

            logger.info(f"Reading kit.yaml from {module_path}")

            kit = YAMLUtils.read_kit(module_path)

            if not kit.get('workspace', {}).get('files'):
                return []

            workspace_path = self.workspace_base / module_info.workspace_name

            if not workspace_path.exists():
                logger.warning(f"Workspace path does not exist: {workspace_path}")
                return []

            resources = []
            for file_spec in kit['workspace']['files']:
                pattern = file_spec['path']
                # Determine if recursion is needed based on pattern
                recursive = "**" in pattern
                # Use Path.glob for better object handling
                matched_paths = workspace_path.glob(pattern) if not recursive else workspace_path.rglob(pattern)

                for file_path in matched_paths: # file_path is now a Path object
                    try:
                        # --- START CHANGE ---
                        # Check if it's a file and not in an ignored directory (like .git)
                        relative_path_parts = file_path.relative_to(workspace_path).parts
                        if file_path.is_file() and not (relative_path_parts and relative_path_parts[0] == ".git"):
                            relative_path_str = file_path.relative_to(workspace_path).as_posix()
                            content = self._read_file_content(file_path)
                            resources.append(Resource(
                                path=relative_path_str,
                                name=file_path.name,
                                content=content,
                                description=file_spec.get('description')
                            ))
                        elif file_path.is_dir():
                            logger.debug(f"Skipping directory found by glob: {file_path}")
                        # --- END CHANGE ---
                    except Exception as e:
                        logger.error(f"Failed to process path {file_path} for module {module_id}: {str(e)}")


            return resources

        except (ModuleError, ResourceError) as e:
            logger.error(f"Error getting workspace resources for {module_id}: {e}")
            raise ResourceError(str(e))
        except Exception as e:
            # Catch unexpected errors
            logger.exception(f"Unexpected error getting workspace resources for {module_id}")
            raise ResourceError(f"Unexpected error getting workspace resources: {str(e)}")



    def get_provided_instruction_resources(self, module_id: str, ) -> List[Resource]:
        """Get specification resources"""
        try:
            # Get kit config with full paths populated
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            # Early return if no specifications
            if not kit_config.provide or not kit_config.provide.instructions:
                return []

            resources = []
            # Process each specification resource
            for spec in kit_config.provide.instructions:
                file_path = Path(spec.full_path)
                if file_path.exists():
                    resources.append(Resource(
                        path=spec.path,
                        name=file_path.name,
                        content=self._read_file_content(file_path),
                        description=spec.description
                    ))

            return resources

        except (ModuleError, ResourceError) as e:
            raise ResourceError(str(e))
   