from pathlib import Path
import shutil
import tempfile
import zipfile
from typing import List, Optional, BinaryIO
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import os

import yaml

class ModuleError(Exception):
    """Base exception for module management errors"""
    pass

class ModuleNotFoundError(ModuleError):
    """Module or version not found"""
    pass

class VersionExistsError(ModuleError):
    """Version already exists"""
    pass

class InvalidVersionError(ModuleError):
    """Invalid semantic version"""
    pass

@dataclass
class ModuleMetadata:
    """Module version metadata"""
    name: str
    version: str
    created_at: str
    size: int
    owner: str = "default"
    doc_version: str = "v1"
    module_id: str = ""
    environment: List[dict] = None
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = []
    
class VersionSort(Enum):
    """Version sorting options"""
    ASCENDING = "asc"
    DESCENDING = "desc"

class ModuleService:
    """Core module management service"""
    
    def __init__(self, base_path: str | Path):
        """
        Initialize module service
        
        Args:
            base_path: Base directory for storing modules
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    @staticmethod
    def validate_semantic_version(version: str) -> bool:
        """
        Validate semantic versioning format (X.Y.Z)
        
        Args:
            version: Version string to validate
            
        Returns:
            bool: True if valid semantic version
        """
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _get_module_path(self, owner: str, module_id: str, version: Optional[str] = None) -> Path:
        """
        Get path for module or specific version using owner/id/version structure
        
        Args:
            owner: Module owner
            module_id: Module identifier
            version: Optional version
            
        Returns:
            Path: Module directory path
        """
        path = self.base_path / owner / module_id
        if version:
            path = path / version
        return path
        
    def _get_metadata(self, module_path: Path) -> Optional[ModuleMetadata]:
        """Get metadata for module version"""
        try:
            stats = module_path.stat()
            
            # Read blueprint.yaml if it exists
            blueprint_path = module_path / "blueprint.yaml"
            blueprint_data = {}
            if blueprint_path.exists():
                with open(blueprint_path) as f:
                    blueprint_data = yaml.safe_load(f)
            
            return ModuleMetadata(
                name=blueprint_data.get('name', module_path.parent.name),
                version=module_path.name,
                created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                size=stats.st_size,
                owner=blueprint_data.get('owner', module_path.parent.parent.name),
                doc_version=blueprint_data.get('docVersion', 'v1'),
                module_id=blueprint_data.get('id', ''),
                environment=blueprint_data.get('environment', [])
            )
        except Exception:
            return None
    

    def _extract_module(self, zip_file: BinaryIO, extract_path: Path) -> None:
        """Extract module contents"""
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
    
    def save_module(self, module_data: BinaryIO) -> ModuleMetadata:
        """
        Save a new module version by extracting info from blueprint.yaml
        
        Args:
            module_data: Module zip file data
                
        Returns:
            ModuleMetadata: Metadata of saved module
                
        Raises:
            ModuleError: If blueprint.yaml is missing or invalid
            InvalidVersionError: If version format is invalid
            VersionExistsError: If version already exists
        """
        # Create temporary directory to extract and inspect module
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Extract to temp directory first
            self._extract_module(module_data, temp_dir)
            
            # Read blueprint.yaml
            blueprint_path = temp_dir / "blueprint.yaml"
            if not blueprint_path.exists():
                raise ModuleError("blueprint.yaml not found in module root")
                
            with open(blueprint_path) as f:
                try:
                    data = yaml.safe_load(f)
                    owner = data.get("owner")
                    module_id = data.get("id")
                    version = data.get("version")
                except Exception as e:
                    raise ModuleError(f"Invalid blueprint.yaml: {str(e)}")

            if not all([owner, module_id, version]):
                raise ModuleError("Missing required fields in blueprint.yaml")
                
            if not self.validate_semantic_version(version):
                raise InvalidVersionError(f"Invalid version format: {version}")
            
            # Get final module path
            module_path = self._get_module_path(owner, module_id, version)
            
            if module_path.exists():
                raise VersionExistsError(
                    f"Version {version} already exists for {owner}/{module_id}"
                )
            
            # Move from temp to final location
            module_path.mkdir(parents=True)
            for item in temp_dir.iterdir():
                shutil.move(str(item), str(module_path))
            
            # Get metadata
            stats = module_path.stat()
            metadata = ModuleMetadata(
                name=data.get('name', module_path.parent.name),
                version=version,
                created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                size=stats.st_size,
                owner=owner,
                doc_version=data.get('docVersion', 'v1'),
                module_id=module_id,
                environment=data.get('environment', [])
            )

            return metadata
            
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir)

            
    def get_all_modules(self, sort_by_name: bool = True) -> List[ModuleMetadata]:
        """
        Get all module versions
        
        Args:
            sort_by_name: Sort results by module name
            
        Returns:
            List[ModuleMetadata]: List of all module versions
        """
        modules = []
        
        # Iterate through owner directories
        for owner_dir in self.base_path.iterdir():
            if owner_dir.is_dir():
                # Iterate through module directories
                for module_dir in owner_dir.iterdir():
                    if module_dir.is_dir():
                        # Iterate through version directories
                        for version_dir in module_dir.iterdir():
                            if version_dir.is_dir():
                                metadata = self._get_metadata(version_dir)
                                if metadata:
                                    modules.append(metadata)
        
        if sort_by_name:
            modules.sort(key=lambda x: (x.name, x.version))
            
        return modules

    def get_module_versions(
        self, 
        owner: str,
        module_id: str,
        sort: VersionSort = VersionSort.ASCENDING
    ) -> List[str]:
        """
        Get all versions of a module
        
        Args:
            owner: Module owner
            module_id: Module identifier
            sort: Version sort order
            
        Returns:
            List[str]: List of versions
            
        Raises:
            ModuleNotFoundError: If module doesn't exist
        """
        module_path = self._get_module_path(owner, module_id)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module not found: {owner}/{module_id}")
        
        versions = []
        for version_dir in module_path.iterdir():
            if version_dir.is_dir() and self.validate_semantic_version(version_dir.name):
                versions.append(version_dir.name)
        
        # Sort versions by components
        versions.sort(
            key=lambda v: [int(x) for x in v.split('.')],
            reverse=(sort == VersionSort.DESCENDING)
        )
        
        return versions

    def get_module_content_path(self, owner: str, module_id: str, version: str) -> Path:
        """
        Get path to module contents
        
        Args:
            owner: Module owner
            module_id: Module identifier
            version: Module version
            
        Returns:
            Path: Path to module contents
            
        Raises:
            ModuleNotFoundError: If module/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")
            
        path = self._get_module_path(owner, module_id, version)
        if not path.exists():
            raise ModuleNotFoundError(f"Module {owner}/{module_id} version {version} not found")
            
        return path

    def delete_module_version(self, owner: str, module_id: str, version: str) -> None:
        """
        Delete specific module version
        
        Args:
            owner: Module owner
            module_id: Module identifier
            version: Version to delete
            
        Raises:
            ModuleNotFoundError: If module/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")
            
        module_path = self._get_module_path(owner, module_id, version)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module {owner}/{module_id} version {version} not found")
        
        try:
            shutil.rmtree(module_path)
            
            # Remove parent directories if empty
            module_dir = module_path.parent
            if not any(module_dir.iterdir()):
                module_dir.rmdir()
                owner_dir = module_dir.parent
                if not any(owner_dir.iterdir()):
                    owner_dir.rmdir()
                    
        except Exception as e:
            raise ModuleError(f"Failed to delete module version: {str(e)}")

    def delete_module(self, owner: str, module_id: str) -> None:
        """
        Delete module and all versions
        
        Args:
            owner: Module owner
            module_id: Module identifier
            
        Raises:
            ModuleNotFoundError: If module not found
        """
        module_path = self._get_module_path(owner, module_id)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module not found: {owner}/{module_id}")
        
        try:
            shutil.rmtree(module_path)
            
            # Remove owner directory if empty
            owner_dir = module_path.parent
            if not any(owner_dir.iterdir()):
                owner_dir.rmdir()
                
        except Exception as e:
            raise ModuleError(f"Failed to delete module: {str(e)}")