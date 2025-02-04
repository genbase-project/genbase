import io
import os
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import case, or_, select
from engine.db.models import Module, ModuleRelation, ProjectModuleMapping
from engine.db.session import SessionLocal
from sqlalchemy.orm import Session
import networkx as nx

from engine.services.storage.repository import (
    RepoNotFoundError,
    RepoService,
)
from engine.services.execution.stage_state import StageStateService
from engine.utils.file import extract_zip
from engine.utils.logging import logger


class RelationType(Enum):
    CONNECTION = "connection"
    CONTEXT = "context"


class ModuleError(Exception):
    """Base exception for module errors"""
    pass


@dataclass
class ModuleMetadata:
    """Module metadata"""
    module_id: str
    module_name: Optional[str]  # New field
    project_id: str
    kit_id: str
    owner: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str
    path: str

    @classmethod
    def from_orm(cls, module: Module, project_mapping: Optional[ProjectModuleMapping] = None) -> 'ModuleMetadata':
        """Convert SQLAlchemy Module object to ModuleMetadata"""
        if project_mapping is None:
            project_mapping = module.project_mappings[0]
            
        return cls(
            module_id=module.module_id,
            module_name=module.module_name,  # New field
            project_id=project_mapping.project_id,
            kit_id=module.kit_id,
            owner=module.owner,
            version=module.version,
            created_at=module.created_at.isoformat(),
            env_vars=module.env_vars,
            repo_name=module.repo_name,
            path=project_mapping.path
        )



class ModuleService:
    """Service for managing modules and their relationships"""

    def __init__(
        self,
        workspace_base: str,
        module_base: str,
        repo_service: RepoService,
        stage_state_service: StageStateService
    ):
        self.workspace_base = Path(workspace_base)
        self.repo_service = repo_service
        self.stage_state_service = stage_state_service
        self.module_base = module_base


    def _get_db(self) -> Session:
        return SessionLocal()


    def _validate_path(self, path: str) -> bool:
        """
        Validate module path format (alphanumeric segments separated by dots)
        Example valid paths: "abc.123", "service.auth.v1", "backend.users"
        """
        path_pattern = r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$'
        return bool(re.match(path_pattern, path))

    def create_module(
        self,
        project_id: str,
        owner: str,
        kit_id: str,
        version: str,
        env_vars: Dict[str, str],
        path: str,
        module_name: Optional[str] = None  # New optional parameter
    ) -> ModuleMetadata:
        """Create module with path"""
        if not self._validate_path(path):
            raise ModuleError("Invalid path format. Path must be alphanumeric segments separated by dots")

        module_id = str(uuid.uuid4())
        repo_name = f"{module_id}"
        created_at = datetime.now(UTC).isoformat()

        try:
            # Get workspace path
            workspace_path = self.workspace_base / owner / kit_id / version / "workspace"
            if not workspace_path.exists():
                raise ModuleError(f"Workspace not found for {owner}/{kit_id} v{version}")

            # Create in-memory zip of workspace
            memory_zip = io.BytesIO()
            with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(workspace_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(workspace_path)
                        zipf.write(file_path, arcname)

            memory_zip.seek(0)

            # Create repository
            self.repo_service.create_repository(
                repo_name=repo_name,
                content_file=memory_zip,
                filename="workspace.zip",
                extract_func=extract_zip
            )

            with self._get_db() as db:
                # Create module
                module = Module(
                    module_id=module_id,
                    kit_id=kit_id,
                    module_name=module_name or module_id,
                    owner=owner,
                    version=version,
                    created_at=created_at,
                    env_vars=env_vars,
                    repo_name=repo_name
                )
                db.add(module)

                # Create project mapping
                mapping = ProjectModuleMapping(
                    project_id=project_id,
                    module_id=module_id,
                    path=path,
                    created_at=created_at,
                    updated_at=created_at
                )
                db.add(mapping)
                
                db.commit()
                db.refresh(module)

                self.stage_state_service.initialize_module(module_id)
                logger.info(f"Created module {module_id} for {owner}/{kit_id} v{version}")

                return ModuleMetadata.from_orm(module, mapping)


        except Exception as e:
            # Cleanup on failure
            try:
                self.repo_service.delete_repository(repo_name)
            except:
                pass
            raise ModuleError(f"Failed to create module: {str(e)}")



    def update_module_path(self, module_id: str, project_id: str, new_path: str):
        """Update module path in a project"""
        if not self._validate_path(new_path):
            raise ModuleError("Invalid path format. Path must be alphanumeric segments separated by dots")

        try:
            with self._get_db() as db:
                mapping = db.query(ProjectModuleMapping).filter_by(
                    module_id=module_id,
                    project_id=project_id
                ).first()

                if not mapping:
                    raise ModuleError("Module not found in specified project")

                mapping.path = new_path
                mapping.updated_at = datetime.now(UTC)
                db.commit()

        except Exception as e:
            raise ModuleError(f"Failed to update module path: {str(e)}")

    def get_project_modules(self, project_id: str) -> List[ModuleMetadata]:
        """Get all modules for a project"""
        try:
            with self._get_db() as db:
                stmt = (
                    select(Module, ProjectModuleMapping)
                    .join(ProjectModuleMapping)
                    .where(ProjectModuleMapping.project_id == project_id)
                )
                results = db.execute(stmt).all()
                return [
                    ModuleMetadata.from_orm(module, mapping)
                    for module, mapping in results
                ]

        except Exception as e:
            raise ModuleError(f"Failed to get project modules: {str(e)}")


    def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        description: Optional[str] = None  # Add description parameter
    ):
        """Create relationship between modules with optional description"""
        try:
            with self._get_db() as db:
                relation = ModuleRelation(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type.value,
                    created_at=datetime.now(UTC),
                    description=description  # Add description field
                )
                db.add(relation)
                db.commit()

        except Exception as e:
            raise ModuleError(f"Failed to create relation: {str(e)}")



    def update_relation_description(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        description: str
    ):
        """Update the description of an existing module relation"""
        try:
            with self._get_db() as db:
                relation = db.query(ModuleRelation).filter_by(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type.value
                ).first()
                
                if not relation:
                    raise ModuleError("Relation not found")
                    
                relation.description = description
                db.commit()

        except Exception as e:
            raise ModuleError(f"Failed to update relation description: {str(e)}")


    def delete_relation(self, source_id: str, target_id: str, relation_type: RelationType):
        """Delete relationship between modules"""
        try:
            with self._get_db() as db:
                db.query(ModuleRelation).filter_by(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type.value
                ).delete()
                db.commit()

        except Exception as e:
            raise ModuleError(f"Failed to delete relation: {str(e)}")


    def get_module_graph(self) -> nx.DiGraph:
        """Get NetworkX graph of module relationships"""
        graph = nx.MultiDiGraph()

        try:
            with self._get_db() as db:
                # Get all modules with their project mappings
                stmt = select(Module).join(ProjectModuleMapping)
                modules = db.execute(stmt).scalars().all()

                for module in modules:
                    graph.add_node(
                        module.module_id,
                        kit_id=module.kit_id,
                        owner=module.owner,
                        version=module.version,
                        module_name=module.module_name,
                        created_at=module.created_at,
                        env_vars=module.env_vars,
                        repo_name=module.repo_name,
                        project_id=module.project_mappings[0].project_id,
                        path=module.project_mappings[0].path
                    )

                # Get all relations
                relations = db.query(ModuleRelation).all()

                for relation in relations:
                    graph.add_edge(
                        relation.source_id,
                        relation.target_id,
                        key=f"{relation.source_id}_{relation.target_id}_{relation.relation_type}",
                        type=relation.relation_type,
                        created_at=relation.created_at,
                        description=relation.description
                    )

                return graph

        except Exception as e:
            raise ModuleError(f"Failed to build module graph: {str(e)}")


    def delete_module(self, module_id: str):
        """Delete module and its project mappings"""
        try:
            with self._get_db() as db:
                module = db.query(Module).filter_by(module_id=module_id).first()
                if not module:
                    return

                repo_name = module.repo_name

                # SQLAlchemy will handle cascading deletes based on relationships
                db.delete(module)
                db.commit()

                # Delete repository
                try:
                    self.repo_service.delete_repository(repo_name)
                except RepoNotFoundError:
                    pass

        except Exception as e:
            raise ModuleError(f"Failed to delete module: {str(e)}")



    def get_linked_modules(
        self,
        module_id: str,
        relation_type: Optional[RelationType] = None
    ) -> List[ModuleMetadata]:
        """
        Get modules linked to the specified module. Both CONNECTION and CONTEXT
        relations are bi-directional.
        """
        try:
            with self._get_db() as db:
                # First find the related module IDs
                relation_query = (
                    select(
                        case(
                            (ModuleRelation.source_id == module_id, ModuleRelation.target_id),
                            else_=ModuleRelation.source_id
                        ).label('related_module_id')
                    )
                    .where(or_(
                        ModuleRelation.source_id == module_id,
                        ModuleRelation.target_id == module_id
                    ))
                )

                if relation_type:
                    relation_query = relation_query.where(ModuleRelation.relation_type == relation_type.value)

                # Then get the modules
                stmt = (
                    select(Module, ProjectModuleMapping)
                    .join(ProjectModuleMapping)
                    .where(Module.module_id.in_(relation_query))
                )

                logger.info(f"Relation type: {relation_type}")
                logger.info(f"Query: {stmt}")

                results = db.execute(stmt).all()
                logger.info(f"Results: {results}")
                
                return [
                    ModuleMetadata.from_orm(module, mapping)
                    for module, mapping in results
                ]

        except Exception as e:
            logger.error(f"Error in get_linked_modules: {str(e)}", exc_info=True)
            raise ModuleError(f"Failed to get linked modules: {str(e)}")




    def get_module_metadata(self, module_id: str) -> ModuleMetadata:
        """
        Get metadata for a module
        
        Args:
            module_id: module ID
            
        Returns:
            ModuleMetadata: Module metadata
            
        Raises:
            ModuleError: If module not found
        """
        try:
            with self._get_db() as db:
                result = (
                    db.execute(
                        select(Module, ProjectModuleMapping)
                        .join(ProjectModuleMapping)
                        .filter(Module.module_id == module_id)
                    ).first()
                )

                if not result:
                    raise ModuleError(f"Module {module_id} not found")

                module, mapping = result
                return ModuleMetadata.from_orm(module, mapping)

        except Exception as e:
            raise ModuleError(f"Failed to get module metadata: {str(e)}")


    def get_module_path(self, module_id: str) -> Path:
        """Get module path"""

        module_info = self.get_module_metadata(module_id)

        return Path(self.module_base) / module_info.owner / module_info.kit_id / module_info.version



    def update_module_name(self, module_id: str, new_name: str):
        """
        Update module name
        
        Args:
            module_id: Module ID
            new_name: New module name
            
        Raises:
            ModuleError: If module not found or update fails
        """
        try:
            with self._get_db() as db:
                module = db.query(Module).filter_by(module_id=module_id).first()

                
                if not module:
                    raise ModuleError(f"Module {module_id} not found")
                    
                module.module_name = new_name
                module.updated_at = datetime.now(UTC)  # Add this if you want to track updates
                db.commit()
                
                logger.info(f"Updated name for module {module_id} to: {new_name}")
                
                return ModuleMetadata.from_orm(module, module.project_mappings[0])
                
        except Exception as e:
            raise ModuleError(f"Failed to update module name: {str(e)}")
        


    def get_relation_description(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType
    ) -> Optional[str]:
        """Get the description of a module relation"""
        try:
            with self._get_db() as db:
                relation = db.query(ModuleRelation).filter_by(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type.value
                ).first()
                
                if not relation:
                    raise ModuleError("Relation not found")
                    
                return relation.description
        except Exception as e:
            raise ModuleError(f"Failed to get relation description: {str(e)}")
