from fastapi import APIRouter
from pathlib import Path
import glob
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import yaml
from engine.services.runtime_module import RuntimeModuleService, RuntimeModuleError

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
        runtime_service: RuntimeModuleService
    ):
        self.workspace_base = Path(workspace_base)
        self.module_base = Path(module_base)
        self.repo_base = Path(repo_base)
        self.runtime_service = runtime_service

    def _read_blueprint(self, module_path: Path) -> dict:
        """Read and parse blueprint.yaml"""
        blueprint_path = module_path / "blueprint.yaml"
        if not blueprint_path.exists():
            raise ResourceError("blueprint.yaml not found")
            
        try:
            with open(blueprint_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ResourceError(f"Failed to parse blueprint.yaml: {str(e)}")

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content safely"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ResourceError(f"Failed to read file {file_path}: {str(e)}")

    def get_workspace_resources(self, runtime_id: str) -> List[Resource]:
        """Get workspace resources"""
        try:
            module_info = self.runtime_service.get_module_metadata(runtime_id)
            module_path = self.module_base / module_info.owner / module_info.module_id / module_info.version
            
            blueprint = self._read_blueprint(module_path)
            if not blueprint.get('workspace', {}).get('files'):
                return []
                
            workspace_path = self.repo_base / module_info.repo_name
            
            if not workspace_path.exists():
                return []
            
            resources = []
            for file_spec in blueprint['workspace']['files']:
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
            
        except (RuntimeModuleError, ResourceError) as e:
            raise ResourceError(str(e))

    def get_documentation_resources(self, runtime_id: str) -> List[Resource]:
        """Get documentation resources"""
        try:
            module_info = self.runtime_service.get_module_metadata(runtime_id)
            module_path = self.module_base / module_info.owner / module_info.module_id / module_info.version
            
            blueprint = self._read_blueprint(module_path)
            if not blueprint.get('instructions', {}).get('documentation'):
                return []
            
            instruction_path = module_path / "instructions"
            if not instruction_path.exists():
                return []
            
            resources = []
            for doc in blueprint['instructions']['documentation']:
                file_path = instruction_path / doc['path']
                if file_path.exists():
                    resources.append(Resource(
                        path=doc['path'],
                        name=file_path.name,
                        content=self._read_file_content(file_path),
                        description=doc.get('description')
                    ))
            
            return resources
            
        except (RuntimeModuleError, ResourceError) as e:
            raise ResourceError(str(e))

    def get_specification_resources(self, runtime_id: str) -> List[Resource]:
        """Get specification resources"""
        try:
            module_info = self.runtime_service.get_module_metadata(runtime_id)
            module_path = self.module_base / module_info.owner / module_info.module_id / module_info.version
            
            blueprint = self._read_blueprint(module_path)
            if not blueprint.get('instructions', {}).get('specification'):
                return []
            
            instruction_path = module_path / "instructions"
            if not instruction_path.exists():
                return []
            
            resources = []
            for spec in blueprint['instructions']['specification']:
                file_path = instruction_path / spec['path']
                if file_path.exists():
                    resources.append(Resource(
                        path=spec['path'],
                        name=file_path.name,
                        content=self._read_file_content(file_path),
                        description=spec.get('description')
                    ))
            
            return resources
            
        except (RuntimeModuleError, ResourceError) as e:
            raise ResourceError(str(e))