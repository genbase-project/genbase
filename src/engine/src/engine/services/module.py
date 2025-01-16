from pathlib import Path
import shutil
import zipfile
from typing import List, Optional, BinaryIO
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import os

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
    
    def _get_module_path(self, module_name: str, version: Optional[str] = None) -> Path:
        """Get path for module or specific version"""
        path = self.base_path / module_name
        if version:
            path = path / version
        return path
    
    def _get_metadata(self, module_path: Path) -> Optional[ModuleMetadata]:
        """Get metadata for module version"""
        try:
            stats = module_path.stat()
            return ModuleMetadata(
                name=module_path.parent.name,
                version=module_path.name,
                created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                size=stats.st_size
            )
        except Exception:
            return None
    
    def _extract_module(self, zip_file: BinaryIO, extract_path: Path) -> None:
        """Extract module contents"""
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
    
    def save_module(self, module_name: str, version: str, module_data: BinaryIO) -> ModuleMetadata:
        """
        Save a new module version
        
        Args:
            module_name: Name of the module
            version: Semantic version
            module_data: Module zip file data
            
        Returns:
            ModuleMetadata: Metadata of saved module
            
        Raises:
            InvalidVersionError: If version format is invalid
            VersionExistsError: If version already exists
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version format: {version}")
        
        module_path = self._get_module_path(module_name, version)
        
        if module_path.exists():
            raise VersionExistsError(f"Version {version} already exists for {module_name}")
        
        try:
            module_path.mkdir(parents=True)
            
            # Extract module contents
            self._extract_module(module_data, module_path)
            
            metadata = self._get_metadata(module_path)
            if not metadata:
                raise ModuleError("Failed to get module metadata")
                
            return metadata
            
        except Exception as e:
            if module_path.exists():
                shutil.rmtree(module_path)
            raise ModuleError(f"Failed to save module: {str(e)}")
    
    def get_all_modules(self, sort_by_name: bool = True) -> List[ModuleMetadata]:
        """
        Get all module versions
        
        Args:
            sort_by_name: Sort results by module name
            
        Returns:
            List[ModuleMetadata]: List of all module versions
        """
        modules = []
        
        for module_dir in self.base_path.iterdir():
            if module_dir.is_dir():
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
        module_name: str,
        sort: VersionSort = VersionSort.ASCENDING
    ) -> List[str]:
        """
        Get all versions of a module
        
        Args:
            module_name: Module name
            sort: Version sort order
            
        Returns:
            List[str]: List of versions
            
        Raises:
            ModuleNotFoundError: If module doesn't exist
        """
        module_path = self._get_module_path(module_name)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module not found: {module_name}")
        
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
    
    def get_module_content_path(self, module_name: str, version: str) -> Path:
        """
        Get path to module contents
        
        Args:
            module_name: Module name
            version: Module version
            
        Returns:
            Path: Path to module contents
            
        Raises:
            ModuleNotFoundError: If module/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")
            
        path = self._get_module_path(module_name, version)
        if not path.exists():
            raise ModuleNotFoundError(f"Module {module_name} version {version} not found")
            
        return path
    
    def delete_module_version(self, module_name: str, version: str) -> None:
        """
        Delete specific module version
        
        Args:
            module_name: Module name
            version: Version to delete
            
        Raises:
            ModuleNotFoundError: If module/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")
            
        module_path = self._get_module_path(module_name, version)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module {module_name} version {version} not found")
        
        try:
            shutil.rmtree(module_path)
            
            # Remove module directory if empty
            parent_dir = module_path.parent
            if not any(parent_dir.iterdir()):
                parent_dir.rmdir()
                
        except Exception as e:
            raise ModuleError(f"Failed to delete module version: {str(e)}")
    
    def delete_module(self, module_name: str) -> None:
        """
        Delete module and all versions
        
        Args:
            module_name: Module to delete
            
        Raises:
            ModuleNotFoundError: If module not found
        """
        module_path = self._get_module_path(module_name)
        
        if not module_path.exists():
            raise ModuleNotFoundError(f"Module not found: {module_name}")
        
        try:
            shutil.rmtree(module_path)
        except Exception as e:
            raise ModuleError(f"Failed to delete module: {str(e)}")