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
from engine.db.models import WorkManifest, ChatHistory
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

    def get_documentation_resources(self, module_id: str) -> List[Resource]:
        """Get documentation resources"""
        try:
            # Get kit config with full paths populated
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            # Early return if no documentation
            if not kit_config.instructions or not kit_config.instructions.documentation:
                return []

            resources = []
            # Process each documentation resource
            for doc in kit_config.instructions.documentation:
                file_path = Path(doc.full_path)
                if file_path.exists():
                    resources.append(Resource(
                        path=doc.path,
                        name=file_path.name,
                        content=self._read_file_content(file_path),
                        description=doc.description
                    ))

            return resources

        except (ModuleError, ResourceError) as e:
            raise ResourceError(str(e))

    def get_specification_resources(self, module_id: str) -> List[Resource]:
        """Get specification resources"""
        try:
            # Get kit config with full paths populated
            kit_config = self.module_service.get_module_kit_config(module_id)
            
            # Early return if no specifications
            if not kit_config.instructions or not kit_config.instructions.specification:
                return []

            resources = []
            # Process each specification resource
            for spec in kit_config.instructions.specification:
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
            
    def _get_recent_chat_history(self, module_id: str, db: Session, limit: int = 10) -> str:
        """Get recent chat history across all workflows"""
        try:
            messages = (
                db.query(ChatHistory)
                .filter(ChatHistory.module_id == module_id)
                .order_by(desc(ChatHistory.timestamp))
                .limit(limit)
                .all()
            )
            
            # Format chat history
            formatted_messages = []
            for msg in reversed(messages):  # Show in chronological order
                formatted_messages.append(
                    f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {msg.workflow}]\n"
                    f"{msg.role}: {msg.content}\n"
                )
                
            return "\n".join(formatted_messages)
        except Exception as e:
            logger.warning(f"Error getting chat history: {str(e)}")
            return ""
            
    async def generate_work_manifest(self, module_id: str, db: Session) -> Optional[Resource]:
        """Generate and store a work manifest for the module"""
        try:
            # Get workspace files content
            workspace_files = self.get_workspace_resources(module_id)
            files_content = "\n\n".join([f"File: {res.path}\n{res.content}" for res in workspace_files])
            
            # Get recent chat history
            chat_history = self._get_recent_chat_history(module_id, db)
            
            # Prepare prompt for the model
            prompt = f"""Based on the following repository files and recent chat history, generate a markdown document 
            that explains the current state of the module. Focus on:
            1. Key files and their purposes
            2. Recent changes and their impact
            3. Current development status
            4. Potential next steps

            Repository files:
            {files_content}

            Recent chat history:
            {chat_history}
            """
            
            # Generate manifest using model
            if not self.model_service:
                raise ResourceError("Model service not initialized")
                
            response = await self.model_service.chat_completion(
                messages=[{
                    "role": "system",
                    "content": "You are a technical documentation expert responsible for generating clear and concise module state descriptions."
                },
                {
                    "role": "user",
                    "content": prompt
                }]
            )
            
            manifest_content = response.choices[0].message.content
            
            # Store in database
            manifest = WorkManifest(
                module_id=module_id,
                content=manifest_content,
                timestamp=datetime.now(UTC)
            )
            db.add(manifest)
            db.commit()
            
            # Return as resource
            timestamp = manifest.timestamp.strftime("%Y%m%d_%H%M%S")
            return Resource(
                path=f"manifest_{timestamp}.md",
                name=f"Manifest {timestamp}.md",
                content=manifest_content,
                description="AI-generated work manifest describing current module state"
            )
            
        except Exception as e:
            raise ResourceError(f"Failed to generate work manifest: {str(e)}")
            
    def get_manifest_resources(self, module_id: str, db: Session) -> List[Resource]:
        """Get all work manifests for a module"""
        try:
            manifests = (
                db.query(WorkManifest)
                .filter(WorkManifest.module_id == module_id)
                .order_by(desc(WorkManifest.timestamp))
                .all()
            )
            
            return [
                Resource(
                    path=f"manifest_{m.timestamp.strftime('%Y%m%d_%H%M%S')}.md",
                    name=f"Manifest {m.timestamp.strftime('%Y-%m-%d %H:%M:%S')}.md", 
                    content=m.content,
                    description="AI-generated work manifest describing module state"
                )
                for m in manifests
            ]
            
        except Exception as e:
            raise ResourceError(f"Failed to get work manifests: {str(e)}")
