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
from sqlalchemy import and_, case, delete, or_, select, update
from engine.db.models import Module, ModuleProvide, ProjectModuleMapping, ProvideType
from engine.db.session import SessionLocal
from sqlalchemy.orm import Session
import networkx as nx

from engine.services.storage.repository import (
    WorkspaceNotFoundError,
    WorkspaceService,
)
from engine.services.execution.state import StateService
from engine.services.core.kit import KitService, KitConfig
from engine.utils.file import extract_zip
from loguru import logger

from engine.utils.readable_uid import generate_readable_uid




class ModuleError(Exception):
    """Base exception for module errors"""
    pass

class ConnectionAccessError(ModuleError):
    """No connection access to target module"""
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
        repo_service: WorkspaceService,
        state_service: StateService,
        kit_service: KitService
    ):
        self.workspace_base = Path(workspace_base)
        self.repo_service = repo_service
        self.state_service = state_service
        self.module_base = module_base
        self.kit_service = kit_service


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

        module_id = generate_readable_uid()
        repo_name = f"{module_id}"
        created_at = datetime.now(UTC)

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
            self.repo_service.create_workspace(
                workspace_name=repo_name,
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

                self.state_service.initialize_module(module_id)
                logger.info(f"Created module {module_id} for {owner}/{kit_id} v{version}")

                return ModuleMetadata.from_orm(module, mapping)


        except Exception as e:
            # Cleanup on failure
            try:
                self.repo_service.delete_workspace(repo_name)
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




    def get_module_graph(self) -> nx.DiGraph:
        """Get graph of module relationships"""
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

                #?TODO: Get module provide

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
                    self.repo_service.delete_workspace(repo_name)
                except WorkspaceNotFoundError:
                    pass

        except Exception as e:
            raise ModuleError(f"Failed to delete module: {str(e)}")





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
        


    def update_module_env_var(
        self,
        module_id: str,
        env_var_name: str,
        env_var_value: str
    ):
        """
        Update/set environment variable for a module
        
        Args:
            module_id: Module ID
            env_var_name: Environment variable name
            env_var_value: Environment variable value
            
        Raises:
            ModuleError: If module not found or update fails
        """
        try:
            with self._get_db() as db:
                module = db.query(Module).filter_by(module_id=module_id).first()
                
                if not module:
                    raise ModuleError(f"Module {module_id} not found")
                    
                # Get current env vars and update
                env_vars = module.env_vars.copy()
                env_vars[env_var_name] = env_var_value
                
                # Assign the whole dict back to trigger SQLAlchemy change detection
                module.env_vars = env_vars
                module.updated_at = datetime.now(UTC)
                db.commit()
                db.refresh(module)  # Refresh to ensure we have latest state
                
                logger.info(f"Updated env var {env_var_name} for module {module_id}")
                
                return ModuleMetadata.from_orm(module, module.project_mappings[0])
                
        except Exception as e:
            raise ModuleError(f"Failed to update module env var: {str(e)}")

    def get_module_kit_config(self, module_id: str) -> KitConfig:
        """
        Get kit configuration for a module
        
        Args:
            module_id: Module ID
            
        Returns:
            KitConfig: Complete kit configuration
            
        Raises:
            ModuleError: If module not found or kit config cannot be retrieved
        """
        try:
            metadata = self.get_module_metadata(module_id)
            return self.kit_service.get_kit_config(
                owner=metadata.owner,
                kit_id=metadata.kit_id,
                version=metadata.version
            )
        except Exception as e:
            raise ModuleError(f"Failed to get kit config: {str(e)}")




    def create_module_provide(
        self, 
        provider_id: str, 
        receiver_id: str, 
        resource_type: ProvideType,
        description: Optional[str] = None
    ) -> ModuleProvide:
        """
        Create a new provide relationship between modules
        
        Args:
            provider_id: ID of module providing the resource
            receiver_id: ID of module receiving the resource
            resource_type: Type of resource being provided (TOOL or WORKSPACE)
            description: Optional description of the provide relationship
            
        Returns:
            The created ModuleProvide instance
            
        Raises:
            ValueError: If either module does not exist
        """
        # Validate that both modules exist
        db = self._get_db()
        provider = db.get(Module, provider_id)
        receiver = db.get(Module, receiver_id)
        
        if not provider:
            raise ValueError(f"Provider module with ID {provider_id} not found")
        if not receiver:
            raise ValueError(f"Receiver module with ID {receiver_id} not found")
        
        # Create the provide relationship
        now = datetime.now(UTC)
        provide = ModuleProvide(
            provider_id=provider_id,
            receiver_id=receiver_id,
            resource_type=resource_type,
            description=description,
            created_at=now,
            updated_at=now
        )
        
        db.add(provide)
        db.commit()
        db.refresh(provide)
        
        return provide


    def get_module_provides(
        self, 
        module_id: str, 
        as_provider: bool = True,
        resource_type: Optional[ProvideType] = None
    ) -> List[ModuleProvide]:
        """
        Get all provide relationships for a module
        
        Args:
            module_id: ID of the module
            as_provider: If True, get relationships where module is provider,
                        otherwise get relationships where module is receiver
            resource_type: Optional filter by resource type
            
        Returns:
            List of ModuleProvide instances
        """
        db = self._get_db()
        query = None
        if as_provider:
            query = select(ModuleProvide).where(ModuleProvide.provider_id == module_id)
        else:
            query = select(ModuleProvide).where(ModuleProvide.receiver_id == module_id)
            
        if resource_type:
            query = query.where(ModuleProvide.resource_type == resource_type)
            
        result = db.execute(query)
        return list(result.scalars().all())


    def delete_module_provide(
        self, 
        provider_id: str, 
        receiver_id: str, 
        resource_type: ProvideType
    ) -> bool:
        """
        Delete a provide relationship between modules
        
        Args:
            provider_id: ID of provider module
            receiver_id: ID of receiver module
            resource_type: Type of resource
            
        Returns:
            True if relationship was deleted, False if it didn't exist
        """
        db = self._get_db()
        query = delete(ModuleProvide).where(
            ModuleProvide.provider_id == provider_id,
            ModuleProvide.receiver_id == receiver_id,
            ModuleProvide.resource_type == resource_type
        )
        
        result = db.execute(query)
        db.commit()
        
        return result.rowcount > 0


    def get_modules_with_access_to(
        self, 
        module_id: str, 
        resource_type: ProvideType
    ) -> List[Module]:
        """
        Get all modules that have access to specified resources of a module
        
        Args:
            module_id: ID of the provider module
            resource_type: Type of resource
            
        Returns:
            List of Module instances that have access
        """
        db = self._get_db()
        query = select(Module).join(
            ModuleProvide, 
            and_(
                ModuleProvide.receiver_id == Module.module_id,
                ModuleProvide.provider_id == module_id,
                ModuleProvide.resource_type == resource_type
            )
        )
        
        result = db.execute(query)
        return list(result.scalars().all())


    def get_modules_providing_to(
        self, 
        module_id: str, 
        resource_type: ProvideType
    ) -> List[Module]:
        """
        Get all modules that provide specified resources to a module
        
        Args:
            module_id: ID of the receiver module
            resource_type: Type of resource
            
        Returns:
            List of Module instances that provide access
        """
        db = self._get_db()
        query = select(Module).join(
            ModuleProvide, 
            and_(
                ModuleProvide.provider_id == Module.module_id,
                ModuleProvide.receiver_id == module_id,
                ModuleProvide.resource_type == resource_type
            )
        )
        
        result = db.execute(query)
        return list(result.scalars().all())


    def update_module_provide_description(
        self,
        provider_id: str,
        receiver_id: str,
        resource_type: ProvideType,
        description: str
    ) -> bool:
        """
        Update the description of a provide relationship
        
        Args:
            provider_id: ID of provider module
            receiver_id: ID of receiver module
            resource_type: Type of resource
            description: New description
            
        Returns:
            True if relationship was updated, False if it didn't exist
        """
        db = self._get_db()
        query = update(ModuleProvide).where(
            ModuleProvide.provider_id == provider_id,
            ModuleProvide.receiver_id == receiver_id,
            ModuleProvide.resource_type == resource_type
        ).values(
            description=description,
            updated_at=datetime.now(UTC)
        )
        
        result = db.execute(query)
        db.commit()
        
        return result.rowcount > 0








    def create_module_provide(
        self, 
        provider_id: str, 
        receiver_id: str, 
        resource_type: ProvideType,
        description: Optional[str] = None
    ) -> ModuleProvide:
        """
        Create a new provide relationship between modules
        
        Args:
            provider_id: ID of module providing the resource
            receiver_id: ID of module receiving the resource
            resource_type: Type of resource being provided (TOOL or WORKSPACE)
            description: Optional description of the provide relationship
            
        Returns:
            The created ModuleProvide instance
            
        Raises:
            ValueError: If either module does not exist
        """
        # Validate that both modules exist
        db = self._get_db()
        provider = db.get(Module, provider_id)
        receiver = db.get(Module, receiver_id)
        
        if not provider:
            raise ValueError(f"Provider module with ID {provider_id} not found")
        if not receiver:
            raise ValueError(f"Receiver module with ID {receiver_id} not found")
        
        # Create the provide relationship
        now = datetime.now(UTC)
        provide = ModuleProvide(
            provider_id=provider_id,
            receiver_id=receiver_id,
            resource_type=resource_type,
            description=description,
            created_at=now,
            updated_at=now
        )
        
        db.add(provide)
        db.commit()
        db.refresh(provide)
        
        # If providing WORKSPACE, add provider's repo as submodule to receiver's repo
        if resource_type == ProvideType.WORKSPACE:
            try:
                provider_metadata = self.get_module_metadata(provider_id)
                receiver_metadata = self.get_module_metadata(receiver_id)
                
                # Add provider's repo as submodule to receiver's repo within a dedicated workspaces folder
                submodule_path = f"workspaces/{provider_metadata.module_id}"
                self.repo_service.add_submodule(
                    parent_workspace_name=receiver_metadata.repo_name,
                    child_workspace_name=provider_metadata.repo_name,
                    path=submodule_path  # Place in workspaces/module_id
                )
                
                logger.info(f"Added submodule from {provider_id} to {receiver_id}")
            except Exception as e:
                # If submodule creation fails, roll back the provide relationship
                db.delete(provide)
                db.commit()
                raise ModuleError(f"Failed to add submodule while creating provide relationship: {str(e)}")
        
        return provide


    def delete_module_provide(
        self, 
        provider_id: str, 
        receiver_id: str, 
        resource_type: ProvideType
    ) -> bool:
        """
        Delete a provide relationship between modules
        
        Args:
            provider_id: ID of provider module
            receiver_id: ID of receiver module
            resource_type: Type of resource
            
        Returns:
            True if relationship was deleted, False if it didn't exist
        """
        db = self._get_db()
        
        # First check if the relationship exists
        provide_query = select(ModuleProvide).where(
            ModuleProvide.provider_id == provider_id,
            ModuleProvide.receiver_id == receiver_id,
            ModuleProvide.resource_type == resource_type
        )
        provide = db.execute(provide_query).scalar_one_or_none()
        
        if not provide:
            return False
        
        # If deleting WORKSPACE relationship, remove submodule
        if resource_type == ProvideType.WORKSPACE:
            try:
                provider_metadata = self.get_module_metadata(provider_id)
                receiver_metadata = self.get_module_metadata(receiver_id)
                
                # Remove the submodule from receiver's repo
                submodule_path = f"workspaces/{provider_metadata.module_id}"
                self.repo_service.remove_submodule(
                    workspace_name=receiver_metadata.repo_name,
                    submodule_path=submodule_path  # Using workspaces/module_id path
                )
                
                logger.info(f"Removed submodule of {provider_id} from {receiver_id}")
            except Exception as e:
                logger.error(f"Failed to remove submodule while deleting provide relationship: {str(e)}")
                # Continue with deletion of relationship even if submodule removal fails
        
        # Delete the relationship
        query = delete(ModuleProvide).where(
            ModuleProvide.provider_id == provider_id,
            ModuleProvide.receiver_id == receiver_id,
            ModuleProvide.resource_type == resource_type
        )
        
        result = db.execute(query)
        db.commit()
        
        return result.rowcount > 0