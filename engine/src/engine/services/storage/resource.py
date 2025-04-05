import glob
from pathlib import Path
from typing import List, Optional
from datetime import datetime, UTC
import glob
from sqlalchemy import desc

import yaml
from engine.services.execution.model import ModelService
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
        workspace_base: str | Path,
        module_base: str | Path,
        repo_base: str | Path,
        module_service: ModuleService,
        model_service: ModelService
    ):
        self.workspace_base = Path(workspace_base)
        self.module_base = Path(module_base)
        self.repo_base = Path(repo_base)
        self.module_service = module_service
        self.model_service = model_service



    def _read_file_content(self, file_path: Path) -> str:
        """Read file content safely"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ResourceError(f"Failed to read file {file_path}: {str(e)}")

    def get_workspace_resources(self, module_id: str) -> List[Resource]:
        """Get workspace resources"""
        try:
            module_info = self.module_service.get_module_metadata(module_id)
            module_path = self.module_service.get_module_path(module_id)
            logger.info(f"Getting workspace resources for module {module_info}")

            logger.info(f"Reading kit.yaml from {module_path}")

            kit = YAMLUtils.read_kit(module_path)

            if not kit.get('workspace', {}).get('files'):
                return []

            workspace_path = self.repo_base / module_info.repo_name

            if not workspace_path.exists():
                return []

            resources = []
            for file_spec in kit['workspace']['files']:
                pattern = file_spec['path']
                matched_files = glob.glob(str(workspace_path / pattern), recursive=True)

                for file_path in matched_files:
                    relative_path = Path(file_path).relative_to(workspace_path).as_posix()
                    resources.append(Resource(
                        path=relative_path,
                        name=Path(file_path).name,
                        content=self._read_file_content(Path(file_path)),
                        description=file_spec.get('description')
                    ))

            return resources

        except (ModuleError, ResourceError) as e:
            raise ResourceError(str(e))


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
   