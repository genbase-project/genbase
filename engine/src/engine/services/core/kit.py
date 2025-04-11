import io
import json
import os
import pathlib
import re
import shutil
import tarfile
import tempfile
import zipfile
from urllib.parse import urljoin

import httpx
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from loguru import logger
import yaml

@dataclass
class EnvironmentVariable:
    """Environment variable definition"""
    name: str
    description: str
    required: bool = False
    default: Optional[str] = None

@dataclass
class Agent:
    """Agent configuration"""
    name: str
    class_name: str  # Maps to 'class' in YAML
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        return cls(
            name=data['name'],
            class_name=data['class'],
            description=data.get('description')
        )

@dataclass
class InstructionItem:
    """Instruction item definition"""
    name: str
    path: str  # Original path from config
    description: Optional[str] = None
    full_path: str = ""  # Full filesystem path constructed as module_path/instructions/path
    module_id: Optional[str] = None  # Module ID for the instruction
    content: str = ""

@dataclass
class ProfileTool:
    """Profile tool definition"""
    path: str  # Original path in format "module:function" or just "function"
    name: str
    description: Optional[str] = None
    full_file_path: str = ""  # Full path to the tool file
    function_name: str = ""  # Function name extracted from path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "description": self.description,
            "full_file_path": self.full_file_path,
            "function_name": self.function_name
        }
    
    @classmethod
    def resolve_path(cls, path: str, kit_path: Path) -> Tuple[str, str]:
        """
        Resolve tool path and function name.
        If path doesn't contain a colon, assume it's just a function name in __init__.py
        
        Args:
            path: Tool path in format "module:function" or just "function"
            kit_path: Base path to kit
            
        Returns:
            Tuple of (full_file_path, function_name)
        """
        if ":" in path:
            # Traditional format: path:function
            tool_file_path, func_name = path.split(":")
            full_file_path = str(kit_path / "tools" / f"{tool_file_path}.py")
        else:
            # New format: just function name, look in __init__.py
            func_name = path
            full_file_path = str(kit_path / "tools" / "__init__.py")
            
        return full_file_path, func_name

@dataclass
class Profile:
    """Profile configuration"""
    agent: str
    tools: List[ProfileTool]
    instructions: List[InstructionItem] = field(default_factory=list)


    @classmethod
    def from_dict(cls, data: Dict[str, Any], kit_path: Optional[Path] = None) -> 'Profile':
        def create_profile_tool(tool: Dict[str, Any]) -> ProfileTool:
            profile_tool = ProfileTool(
                path=tool['path'],
                name=tool['name'],
                description=tool.get('description')
            )
            
            # Use the new resolution method
            full_file_path, func_name = ProfileTool.resolve_path(tool['path'], kit_path)
            profile_tool.full_file_path = full_file_path
            profile_tool.function_name = func_name

            return profile_tool



        instruction_data = []

        for instruction in data.get('instructions', []):
            instruction_item = InstructionItem(
                name=instruction['name'],
                path=instruction['path'],
                description=instruction.get('description'),
                full_path=str(kit_path / "instructions" / instruction['path']),
            )
            instruction_item.full_path = str(kit_path / "instructions" / instruction['path'])
            with open(instruction_item.full_path) as f:
                instruction_item.content = f.read()
                
            instruction_data.append(instruction_item)
        
        return cls(
            agent=data['agent'],
            tools=[create_profile_tool(tool) for tool in data.get('tools', [])],
            instructions=instruction_data
        )

@dataclass
class WorkspaceFile:
    """Workspace file definition"""
    path: str
    description: Optional[str] = None

@dataclass
class WorkspaceConfig:
    """Workspace configuration"""
    files: List[WorkspaceFile] = field(default_factory=list)
    ignore: List[str] = field(default_factory=list)


@dataclass
class Port:
    """Container Port"""
    port: int
    name: Optional[str]




@dataclass
class WorkspaceProvide:
    """Workspace definition for provide section"""
    description: Optional[str] = None

@dataclass
class Provide:
    """Resources provided by the kit"""
    tools: List[ProfileTool] = field(default_factory=list)
    instructions: List[InstructionItem] = field(default_factory=list) 
    workspace: Optional[WorkspaceProvide] = None

@dataclass
class KitConfig:
    """Complete kit configuration"""
    doc_version: str
    id: str
    version: str
    name: str
    owner: str
    environment: List[EnvironmentVariable]
    agents: List[Agent]
    profiles: Dict[str, Profile]
    provide: Provide
    dependencies: List[str]
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    image: str = None
    ports: List[Port] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KitConfig':
        # Check if docVersion is v1
        if data.get('docVersion') != 'v1':
            raise KitError(f"Unsupported document version: {data.get('docVersion')}")
            
        # Create provide section
        provide = Provide(
            # Move shared_tools to provide.tools
            tools=[
                ProfileTool(
                    path=tool['path'],
                    name=tool['name'],
                    description=tool.get('description'),
                    # Use the new path resolution logic
                    **_resolve_tool_path(tool['path'], data['kit_path'])
                )
                for tool in data.get('provide', {}).get('tool', [])
            ],
            instructions=[
                InstructionItem(
                    name=item['name'],
                    path=item['path'],
                    description=item.get('description'),
                    full_path=str(data['kit_path'] / "instructions" / item['path']) if data.get('kit_path') else ""
                )
                for item in data.get('provide', {}).get('instructions', [])
            ],
            # Create workspace in provide section
            workspace=WorkspaceProvide(
                description=data.get('provide', {}).get('workspace', {}).get('description')
            ) if data.get('provide', {}).get('workspace') else None
        )

        return cls(
            doc_version=data['docVersion'],
            id=data['id'],
            version=data['version'],
            name=data['name'],
            owner=data['owner'],
            environment=[
                EnvironmentVariable(**env) 
                for env in data.get('environment', [])
            ],
            image=data.get('image', 'python:3.11-slim'),
            agents=[Agent.from_dict(agent) for agent in data.get('agents', [])],
            profiles={
                name: Profile.from_dict(profile, kit_path=data['kit_path'])
                for name, profile in data.get('profiles', {}).items()
            },
            provide=provide,
            dependencies=data.get('dependencies', []),
            workspace=WorkspaceConfig(
                files=[WorkspaceFile(**f) for f in data.get('workspace', {}).get('files', [])],
                ignore=data.get('workspace', {}).get('ignore', [])
            ),
            ports=[Port(**p) for p in data.get('ports', [])]
        )

# Helper function to resolve tool paths
def _resolve_tool_path(path: str, kit_path: Path) -> Dict[str, str]:
    """
    Resolve tool path and return a dictionary with full_file_path and function_name
    
    Args:
        path: Tool path as string (either "path:function" or just "function")
        kit_path: Base kit path
        
    Returns:
        Dict with full_file_path and function_name
    """
    if ":" in path:
        # Traditional format: path:function
        tool_file_path, func_name = path.split(":")
        full_file_path = str(kit_path / "tools" / f"{tool_file_path}.py")
    else:
        # New format: just function name, look in __init__.py
        func_name = path
        full_file_path = str(kit_path / "tools" / "__init__.py")
        
    return {
        "full_file_path": full_file_path,
        "function_name": func_name
    }


class KitError(Exception):
    """Base exception for kit management errors"""
    pass

class RegistryError(KitError):
    """Registry connection or download error"""
    pass

class KitNotFoundError(KitError):
    """Module or version not found"""
    pass

class VersionExistsError(KitError):
    """Version already exists"""
    pass

class InvalidVersionError(KitError):
    """Invalid semantic version"""
    pass



@dataclass
class KitMetadata:
    """Module version metadata"""
    name: str
    version: str
    created_at: str
    size: int
    owner: str = "default"
    doc_version: str = "v1"
    kit_id: str = ""
    environment: List[dict] = None

    def __post_init__(self):
        if self.environment is None:
            self.environment = []

class VersionSort(Enum):
    """Version sorting options"""
    ASCENDING = "asc"
    DESCENDING = "desc"



class KitService:
    """Core kit management service"""

    def __init__(self, base_path: str | Path):
        """
        Initialize kit service
        
        Args:
            base_path: Base directory for storing kits
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)


    def validate_semantic_version(self, version: str) -> bool:
        """
        Validate semantic versioning format (X.Y.Z)
        
        Args:
            version: Version string to validate
            
        Returns:
            bool: True if valid semantic version
        """
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))

    def get_kit_path(self, owner: str, kit_id: str, version: Optional[str] = None) -> Path:
        """
        Get path for kit or specific version using owner/id/version structure
        
        Args:
            owner: Module owner
            kit_id: Module identifier
            version: Optional version
            
        Returns:
            Path: Module directory path
        """
        path = self.base_path / owner / kit_id
        if version:
            path = path / version
        return path



    def _get_metadata(self, kit_path: Path) -> Optional[KitMetadata]:
        """Get metadata for kit version"""
        try:
            stats = kit_path.stat()

            # Read kit.yaml if it exists
            kit_path = kit_path / "kit.yaml"

            logger.debug(f"Reading kit.yaml from {kit_path}")
            kit_data = {}
            if kit_path.exists():
                with open(kit_path) as f:
                    logger.debug(f"Parsing kit.yaml")

                    kit_data = yaml.safe_load(f)


                    logger.debug(f"Parsed kit.yaml: {kit_data}")
            
            return KitMetadata(
                name=kit_data.get('name', kit_path.parent.name),
                version=kit_data.get('version', kit_path.name),
                created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                size=stats.st_size,
                owner=kit_data.get('owner', kit_path.parent.parent.name),
                doc_version=kit_data.get('docVersion', 'v1'),
                kit_id=kit_data.get('id', ''),
                environment=kit_data.get('environment', [])
            )
        except Exception:
            return None


    def _extract_kit(self, zip_file: BinaryIO, extract_path: Path) -> None:
        """Extract kit contents"""
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

  
    def get_kit_config(self, owner: str, kit_id: str, version: str) -> KitConfig:
        """
        Get full kit configuration excluding metadata
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            version: Kit version
            
        Returns:
            KitConfig: Complete kit configuration
            
        Raises:
            KitNotFoundError: If kit/version not found
            KitError: If kit.yaml is invalid or missing
        """
        kit_path = self.get_kit_path(owner, kit_id, version)
        config_path = kit_path / "kit.yaml"
        
        if not config_path.exists():
            raise KitError(f"kit.yaml not found in {kit_path}")
            
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                config_data['kit_path'] = kit_path
                return KitConfig.from_dict(config_data)
        except Exception as e:
            raise KitError(f"Failed to parse kit.yaml: {str(e)}")


    def get_all_kits(self, sort_by_name: bool = True) -> List[KitMetadata]:
        """
        Get all kit versions
        
        Args:
            sort_by_name: Sort results by kit name
            
        Returns:
            List[ModuleMetadata]: List of all kit versions
        """
        kits = []

        # Iterate through owner directories
        for owner_dir in self.base_path.iterdir():
            if owner_dir.is_dir():
                # Iterate through kit directories
                logger.debug(f"Checking owner directory: {owner_dir}")
                for kit_dir in owner_dir.iterdir():
                    if kit_dir.is_dir():
                        # Iterate through version directories
                        logger.debug(f"Checking kit directory: {kit_dir}")
                        for version_dir in kit_dir.iterdir():
                            logger.debug(f"Checking version directory: {version_dir}")
                            if version_dir.is_dir():
                                metadata = self._get_metadata(version_dir)
                                if metadata:
                                    kits.append(metadata)

        logger.debug(f"Found {kits} kits")

        if sort_by_name:
            kits.sort(key=lambda x: (x.name, x.version))

        return kits

    def get_kit_versions(
        self,
        owner: str,
        kit_id: str,
        sort: VersionSort = VersionSort.ASCENDING
    ) -> List[str]:
        """
        Get all versions of a kit
        
        Args:
            owner: Module owner
            kit_id: Module identifier
            sort: Version sort order
            
        Returns:
            List[str]: List of versions
            
        Raises:
            ModuleNotFoundError: If kit doesn't exist
        """
        kit_path = self.get_kit_path(owner, kit_id)

        if not kit_path.exists():
            raise KitNotFoundError(f"Kit not found: {owner}/{kit_id}")

        versions = []
        for version_dir in kit_path.iterdir():
            if version_dir.is_dir() and self.validate_semantic_version(version_dir.name):
                versions.append(version_dir.name)

        # Sort versions by components
        versions.sort(
            key=lambda v: [int(x) for x in v.split('.')],
            reverse=(sort == VersionSort.DESCENDING)
        )

        return versions

    def get_kit_content_path(self, owner: str, kit_id: str, version: str) -> Path:
        """
        Get path to kit contents
        
        Args:
            owner: Module owner
            kit_id: Module identifier
            version: Module version
            
        Returns:
            Path: Path to kit contents
            
        Raises:
            ModuleNotFoundError: If kit/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")

        path = self.get_kit_path(owner, kit_id, version)
        if not path.exists():
            raise KitNotFoundError(f"Module {owner}/{kit_id} version {version} not found")

        return path

    def delete_kit_version(self, owner: str, kit_id: str, version: str) -> None:
        """
        Delete specific kit version
        
        Args:
            owner: Module owner
            kit_id: Module identifier
            version: Version to delete
            
        Raises:
            ModuleNotFoundError: If kit/version not found
            InvalidVersionError: If version format invalid
        """
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version: {version}")

        kit_path = self.get_kit_path(owner, kit_id, version)

        if not kit_path.exists():
            raise KitNotFoundError(f"Module {owner}/{kit_id} version {version} not found")

        try:
            shutil.rmtree(kit_path)

            # Remove parent directories if empty
            kit_dir = kit_path.parent
            if not any(kit_dir.iterdir()):
                kit_dir.rmdir()
                owner_dir = kit_dir.parent
                if not any(owner_dir.iterdir()):
                    owner_dir.rmdir()

        except Exception as e:
            raise KitError(f"Failed to delete kit version: {str(e)}")

    def delete_kit(self, owner: str, kit_id: str) -> None:
        """
        Delete kit and all versions
        
        Args:
            owner: Module owner
            kit_id: Module identifier
            
        Raises:
            ModuleNotFoundError: If kit not found
        """
        kit_path = self.get_kit_path(owner, kit_id)

        if not kit_path.exists():
            raise KitNotFoundError(f"Kit not found: {owner}/{kit_id}")

        try:
            shutil.rmtree(kit_path)

            # Remove owner directory if empty
            owner_dir = kit_path.parent
            if not any(owner_dir.iterdir()):
                owner_dir.rmdir()

        except Exception as e:
            raise KitError(f"Failed to delete kit: {str(e)}")



    def save_kit(self, kit_data: BinaryIO, allow_overwrite: bool = True) -> KitMetadata:
        """
        Save a new kit version by extracting it and reading kit.yaml
        
        Args:
            kit_data: Kit file data (tar.gz or zip format)
            allow_overwrite: If True, allows overwriting existing versions
                
        Returns:
            KitMetadata: Metadata of saved kit
                
        Raises:
            KitError: If kit.yaml is missing or invalid
            InvalidVersionError: If version format is invalid
            VersionExistsError: If version already exists and allow_overwrite is False
        """
        # Create temporary directory to extract and inspect kit
        temp_dir = Path(tempfile.mkdtemp())
        extraction_dir = Path(tempfile.mkdtemp())  # Temporary directory for initial extraction
        try:
            import tarfile
            # Extract to the temporary extraction directory
            with tarfile.open(fileobj=kit_data, mode="r:gz") as tar:
                tar.extractall(extraction_dir)
            
            # Get the top-level directory (assuming there's only one)
            top_dirs = list(extraction_dir.iterdir())
            if len(top_dirs) == 1 and top_dirs[0].is_dir():
                # Move contents from the top-level directory to our actual temp_dir
                for item in top_dirs[0].iterdir():
                    if item.is_dir():
                        shutil.copytree(item, temp_dir / item.name)
                    else:
                        shutil.copy2(item, temp_dir)
            else:
                # Fallback if our assumption is wrong
                for item in extraction_dir.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, temp_dir / item.name)
                    else:
                        shutil.copy2(item, temp_dir)
            
            # Read kit.yaml
            kit_path = temp_dir / "kit.yaml"
            if not kit_path.exists():
                raise KitError("kit.yaml not found in kit root")
            with open(kit_path) as f:
                try:
                    data = yaml.safe_load(f)
                    owner = data.get("owner")
                    kit_id = data.get("id")
                    version = data.get("version")
                except Exception as e:
                    raise KitError(f"Invalid kit.yaml: {str(e)}")
            if not all([owner, kit_id, version]):
                raise KitError("Missing required fields in kit.yaml: owner, id, version")
            if not self.validate_semantic_version(version):
                raise InvalidVersionError(f"Invalid version format: {version}")
            
            # Get final kit path
            kit_path = self.get_kit_path(owner, kit_id, version)
            if kit_path.exists():
                if allow_overwrite:
                    # Remove existing version if overwrite is allowed
                    shutil.rmtree(kit_path)
                else:
                    raise VersionExistsError(
                        f"Version {version} already exists for {owner}/{kit_id}"
                    )
            
            # Move from temp to final location
            kit_path.mkdir(parents=True, exist_ok=True)
            for item in temp_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, kit_path / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, kit_path)
            
            # Get metadata
            stats = kit_path.stat()
            metadata = KitMetadata(
                name=data.get('name', kit_id),
                version=version,
                created_at=datetime.now(UTC).isoformat(),
                size=stats.st_size,
                owner=owner,
                doc_version=data.get('docVersion', 'v1'),
                kit_id=kit_id,
                environment=data.get('environment', [])
            )
            return metadata
        finally:
            # Clean up temp directories
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(extraction_dir, ignore_errors=True)


    def get_registry_kits(self) -> List[Dict[str, Any]]:
        """
        Get all kits from the registry and transform them to match the expected RegistryKitResponse model
        
        Returns:
            List[Dict[str, Any]]: List of transformed kit data matching RegistryKitResponse structure
            
        Raises:
            RegistryError: If registry connection fails
            KitError: Other errors during API call
        """
        if not (base_url := os.getenv('REGISTRY_URL')):
            raise KitError("REGISTRY_URL environment variable not set")
            
        # Construct registry URL for kits endpoint
        registry_url = urljoin(base_url, "api/kits")
        
        try:
            with httpx.Client() as client:
                response = client.get(registry_url)
                response.raise_for_status()
                data = response.json()
                
                # Transform raw kit data to match the RegistryKitResponse model
                transformed_kits = []
                
                for kit in data.get("kits", []):
                    # Skip any invalid entries
                    if not all(key in kit for key in ["owner", "id", "version"]):
                        continue
                    
                    try:
                        # Get kit config without downloading the entire archive
                        kit_config = self.get_registry_kit_config(
                            kit["owner"], 
                            kit["id"], 
                            kit["version"]
                        )
                        
                        # Get kit details for download URL
                        kit_detail_url = urljoin(base_url, f"api/kits/{kit['owner']}/{kit['id']}/{kit['version']}")
                        detail_response = client.get(kit_detail_url)
                        
                        if detail_response.status_code != 200:
                            # If can't get details, use a placeholder download URL
                            download_url = f"{base_url}/api/kits/{kit['owner']}/{kit['id']}/{kit['version']}/download"
                        else:
                            detail_data = detail_response.json()
                            download_url = detail_data.get("downloadUrl", "")
                            # If downloadUrl not in response, try alternate field names
                            if not download_url:
                                download_url = detail_data.get("downloadURL", "")
                            # If still no URL, use a placeholder
                            if not download_url:
                                download_url = f"{base_url}/api/kits/{kit['owner']}/{kit['id']}/{kit['version']}/download"
                        
                        # Build a response that matches RegistryKitResponse model
                        transformed_kit = {
                            "fileName": f"{kit['owner']}-{kit['id']}-{kit['version']}.tar.gz",
                            "downloadURL": download_url,
                            "checksum": f"sha256:{kit.get('id', 'unknown')}",  # Placeholder checksum
                            "kitConfig": kit_config,
                            "uploadedAt": kit.get("lastModified", datetime.now(UTC).isoformat())
                        }
                        
                        transformed_kits.append(transformed_kit)
                        
                    except Exception as e:
                        # Log error but continue with other kits
                        print(f"Error processing kit {kit['owner']}/{kit['id']}/{kit['version']}: {str(e)}")
                        continue
                    
                return transformed_kits
        except httpx.HTTPError as e:
            raise RegistryError(f"Failed to get kits from registry: {str(e)}")
        except Exception as e:
            raise KitError(f"Failed to process registry response: {str(e)}")
    

    def install_kit(self, owner: str, kit_id: str, version: str = None) -> KitMetadata:
        """
        Install kit from registry using the new API format
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier  
            version: Optional specific version to install, otherwise latest
            
        Returns:
            KitMetadata: Installed kit metadata
            
        Raises:
            KitNotFoundError: If kit not found in registry
            InvalidVersionError: If version format invalid  
            RegistryError: If registry connection fails
            KitError: Other errors during installation
        """
        if not (base_url := os.getenv('REGISTRY_URL')):
            raise KitError("REGISTRY_URL environment variable not set")
        
        logger.info(f"Installing kit {owner}/{kit_id} version {version} from registry")
            
        # If version is not provided, get all versions and use latest
        if not version:
            try:
                all_kits = self.get_registry_kits()
                # Filter kits for the owner/id and get versions
                versions = []
                for kit in all_kits:
                    kit_config = kit.get("kitConfig", {})
                    if (kit_config.get("owner") == owner and 
                        kit_config.get("id") == kit_id):
                        versions.append(kit_config.get("version"))
                
                if not versions:
                    raise KitNotFoundError(f"No versions found for kit: {owner}/{kit_id}")
                
                # Sort versions by semantic versioning and use latest
                versions.sort(key=lambda v: [int(x) for x in v.split('.')], reverse=True)
                version = versions[0]
            except Exception as e:
                if isinstance(e, KitNotFoundError):
                    raise
                raise KitError(f"Failed to determine latest version: {str(e)}")
        
        if not self.validate_semantic_version(version):
            raise InvalidVersionError(f"Invalid version format: {version}")
            
        # Construct registry URL for specific kit
        registry_url = urljoin(base_url, f"api/kits/{owner}/{kit_id}/{version}")
        
        # Download kit from registry
        try:
            with httpx.Client() as client:
                # First get download URL
                response = client.get(registry_url)
                if response.status_code == 404:
                    raise KitNotFoundError(f"Kit not found in registry: {owner}/{kit_id}/{version}")
                response.raise_for_status()
                
                response_data = response.json()
                download_url = response_data.get("downloadUrl")

                # Try alternate field name if not found
                if not download_url:
                    download_url = response_data.get("downloadURL")
                    
                if not download_url:
                    raise KitError("Download URL not found in registry response")
                
                # Download actual kit file
                download_response = client.get(download_url)
                download_response.raise_for_status()
                kit_data = io.BytesIO(download_response.content)
        except httpx.HTTPError as e:
            raise RegistryError(f"Failed to download kit from registry: {str(e)}")
            
        # Save downloaded kit
        return self.save_kit(kit_data)

    def get_registry_kit_versions(self, owner: str, kit_id: str) -> List[str]:
        """
        Get all available versions of a kit from the registry
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            
        Returns:
            List[str]: List of available versions sorted by semantic versioning (newest first)
            
        Raises:
            RegistryError: If registry connection fails
            KitNotFoundError: If kit not found
        """
        try:
            # Use the existing registry kits function to get all kits
            all_kits = self.get_registry_kits()
            
            # Filter for the specific owner/id and extract versions
            versions = []
            for kit in all_kits:
                kit_config = kit.get("kitConfig", {})
                if (kit_config.get("owner") == owner and 
                    kit_config.get("id") == kit_id):
                    if version := kit_config.get("version"):
                        versions.append(version)
            
            if not versions:
                raise KitNotFoundError(f"Kit not found in registry: {owner}/{kit_id}")
            
            # Sort versions by semantic versioning (newest first)
            versions.sort(key=lambda v: [int(x) for x in v.split('.')], reverse=True)
            
            return versions
        except Exception as e:
            if isinstance(e, KitNotFoundError):
                raise
            raise KitError(f"Failed to get kit versions: {str(e)}")

    def check_registry_kit_exists(self, owner: str, kit_id: str, version: str) -> bool:
        """
        Check if a specific kit version exists in the registry
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            version: Kit version
            
        Returns:
            bool: True if kit exists, False otherwise
        """
        if not (base_url := os.getenv('REGISTRY_URL')):
            raise KitError("REGISTRY_URL environment variable not set")
            
        # Construct registry URL for specific kit
        registry_url = urljoin(base_url, f"api/kits/{owner}/{kit_id}/{version}")
        
        try:
            with httpx.Client() as client:
                response = client.get(registry_url)
                return response.status_code == 200
        except Exception:
            return False
        

    def get_registry_kit_config(self, owner: str, kit_id: str, version: str) -> Dict[str, Any]:
        """
        Get kit configuration (kit.yaml contents) for a specific kit
        
        This method fetches the kit archive from the registry, extracts kit.yaml,
        and returns its contents without saving the full kit locally.
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            version: Kit version
            
        Returns:
            Dict[str, Any]: Parsed kit.yaml contents
            
        Raises:
            KitNotFoundError: If kit not found
            RegistryError: If registry connection fails
            KitError: If kit.yaml cannot be extracted or parsed
        """
        if not (base_url := os.getenv('REGISTRY_URL')):
            raise KitError("REGISTRY_URL environment variable not set")
        
        # Construct registry URL
        registry_url = urljoin(base_url, f"api/kits/{owner}/{kit_id}/{version}")
        
        try:
            with httpx.Client() as client:
                # Get download URL
                response = client.get(registry_url)
                if response.status_code == 404:
                    raise KitNotFoundError(f"Kit not found: {owner}/{kit_id}/{version}")
                response.raise_for_status()
                
                data = response.json()
                download_url = data.get("downloadUrl")
                if not download_url:
                    download_url = data.get("downloadURL")
                    
                if not download_url:
                    raise KitError("Download URL not found in registry response")
                
                # Download the kit archive
                download_response = client.get(download_url)
                download_response.raise_for_status()
                archive_data = download_response.content
                
            # Create a temporary directory for extraction
            temp_dir = Path(tempfile.mkdtemp())
            try:
                # Try to extract as tar.gz
                archive_file = io.BytesIO(archive_data)
                try:
                    import tarfile
                    with tarfile.open(fileobj=archive_file, mode="r:gz") as tar:
                        # Extract only kit.yaml
                        members = [m for m in tar.getmembers() if m.name == "kit.yaml" or m.name.endswith("/kit.yaml")]
                        if not members:
                            raise KitError("kit.yaml not found in archive")
                        
                        for member in members:
                            tar.extract(member, path=temp_dir)
                            
                        # Find kit.yaml in temp_dir
                        for root, _, files in os.walk(temp_dir):
                            for file in files:
                                if file == "kit.yaml":
                                    kit_yaml_path = Path(root) / file
                                    with open(kit_yaml_path) as f:
                                        kit_config = yaml.safe_load(f)
                                        
                                        # Ensure required fields
                                        if not all(key in kit_config for key in ['id', 'version', 'name']):
                                            raise KitError("Invalid kit.yaml: missing required fields")
                                        
                                        # Set owner if not present
                                        if 'owner' not in kit_config:
                                            kit_config['owner'] = owner
                                            
                                        return kit_config
                                        
                        raise KitError("kit.yaml not found in extracted files")
                        
                except (tarfile.ReadError, EOFError) as e:
                    # If tar.gz extraction fails, try as zip
                    archive_file.seek(0)
                    
                    with zipfile.ZipFile(archive_file) as zip_ref:
                        kit_yaml_path = None
                        
                        # Find kit.yaml in zip
                        for info in zip_ref.infolist():
                            if info.filename.endswith("kit.yaml"):
                                kit_yaml_path = info.filename
                                break
                                
                        if not kit_yaml_path:
                            raise KitError("kit.yaml not found in archive")
                            
                        # Extract only kit.yaml
                        zip_ref.extract(kit_yaml_path, path=temp_dir)
                        
                        # Read kit.yaml
                        extracted_path = temp_dir / kit_yaml_path
                        with open(extracted_path) as f:
                            kit_config = yaml.safe_load(f)
                            
                            # Ensure required fields
                            if not all(key in kit_config for key in ['id', 'version', 'name']):
                                raise KitError("Invalid kit.yaml: missing required fields")
                            
                            # Set owner if not present
                            if 'owner' not in kit_config:
                                kit_config['owner'] = owner
                                
                            return kit_config
                
                raise KitError("Failed to extract kit.yaml from archive")
                
            finally:
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except httpx.HTTPError as e:
            raise RegistryError(f"Failed to download kit from registry: {str(e)}")
        except Exception as e:
            if isinstance(e, (KitNotFoundError, RegistryError, KitError)):
                raise
            raise KitError(f"Failed to extract kit config: {str(e)}")