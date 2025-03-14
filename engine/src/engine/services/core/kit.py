import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from urllib.parse import urljoin

import httpx
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

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

@dataclass
class WorkflowAction:
    """Workflow action definition"""
    path: str  # Original path in format "module:function"
    name: str
    description: Optional[str] = None
    full_file_path: str = ""  # Full path to the action file
    function_name: str = ""  # Function name extracted from path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "description": self.description,
            "full_file_path": self.full_file_path,
            "function_name": self.function_name
        }

@dataclass
class Workflow:
    """Workflow configuration"""
    agent: str
    instruction: str
    actions: List[WorkflowAction]
    instruction_file_path: str = ""  # Full path to instruction file
    instruction_content: str = ""  # Instruction content

    @classmethod
    def from_dict(cls, data: Dict[str, Any], kit_path: Optional[Path] = None) -> 'Workflow':
        def create_workflow_action(action: Dict[str, Any]) -> WorkflowAction:
            workflow_action = WorkflowAction(
                path=action['path'],
                name=action['name'],
                description=action.get('description')
            )
            action_file_path, func_name = action['path'].split(':')
            workflow_action.full_file_path = str(kit_path / "actions" / f"{action_file_path}.py")
            workflow_action.function_name = func_name
            return workflow_action

        instruction_file_path = str(kit_path / "instructions" / f"{data['instruction']}")
        with open(instruction_file_path) as f:
            instruction_content = f.read()
        return cls(
            agent=data['agent'],
            instruction=data['instruction'],
            actions=[create_workflow_action(action) for action in data.get('actions', [])],
            instruction_file_path=instruction_file_path,
            instruction_content=instruction_content
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
    actions: List[WorkflowAction] = field(default_factory=list)
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
    workflows: Dict[str, Workflow]
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
            # Move shared_actions to provide.actions
            actions=[
                WorkflowAction(
                    path=action['path'],
                    name=action['name'],
                    description=action.get('description'),
                    full_file_path=str(data['kit_path'] / "actions" / f"{action['path'].split(':')[0]}.py"),
                    function_name=action['path'].split(':')[1]
                )
                for action in data.get('provide', {}).get('actions', [])
            ],
            # Move instruction.specification to provide.instructions
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
            workflows={
                name: Workflow.from_dict(workflow, kit_path=data['kit_path'])
                for name, workflow in data.get('workflows', {}).items()
            },
            provide=provide,
            dependencies=data.get('dependencies', []),
            workspace=WorkspaceConfig(
                files=[WorkspaceFile(**f) for f in data.get('workspace', {}).get('files', [])],
                ignore=data.get('workspace', {}).get('ignore', [])
            ),
            ports=[Port(**p) for p in data.get('ports', [])]
        )



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
            kit_data = {}
            if kit_path.exists():
                with open(kit_path) as f:
                    kit_data = yaml.safe_load(f)

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

    def install_kit(self, owner: str, kit_id: str, version: str = None) -> KitMetadata:
        """
        Install kit from registry
        
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
            
        # Construct registry URL
        base_url = urljoin(base_url, "api/registry/")
        url = urljoin(base_url, f"kit?owner={owner}&id={kit_id}")

        if version:
            if not self.validate_semantic_version(version):
                raise InvalidVersionError(f"Invalid version format: {version}")
            url = urljoin(base_url, f"kit?owner={owner}&id={kit_id}&version={version}")
        # Download kit from registry
        try:
            with httpx.Client() as client:
                # First get kit metadata and download URL
                response = client.get(url)
                if response.status_code == 404:
                    raise KitNotFoundError(f"Kit not found in registry: {owner}/{kit_id}")
                response.raise_for_status()
                
                response_data = json.loads(response.content)
                kit_info = response_data.get("kitConfig", {})
                download_url = response_data.get("downloadURL")
                if not download_url:
                    raise KitError("Download URL not found in registry response")
                
                # Validate kit info
                required_fields = ["owner", "id", "version"]
                if not all(kit_info.get(field) for field in required_fields):
                    raise KitError("Missing required fields in kit metadata")
                
                # Download actual kit zip file
                download_response = client.get(download_url)
                download_response.raise_for_status()
                kit_data = io.BytesIO(download_response.content)
        except httpx.HTTPError as e:
            raise RegistryError(f"Failed to download kit from registry: {str(e)}")
            
        # Save downloaded kit
        return self.save_kit(kit_data)

    def save_kit(self, kit_data: BinaryIO) -> KitMetadata:
        """
        Save a new kit version by extracting info from kit.yaml
        
        Args:
            kit_data: Module zip file data
                
        Returns:
            ModuleMetadata: Metadata of saved kit
                
        Raises:
            ModuleError: If kit.yaml is missing or invalid
            InvalidVersionError: If version format is invalid
            VersionExistsError: If version already exists
        """
        # Create temporary directory to extract and inspect kit
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Extract to temp directory first
            self._extract_kit(kit_data, temp_dir)

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
                raise KitError("Missing required fields in kit.yaml")


            # Get final kit path
            kit_path = self.get_kit_path(owner, kit_id, version)

            if kit_path.exists():
                raise VersionExistsError(
                    f"Version {version} already exists for {owner}/{kit_id}"
                )

            # Move from temp to final location
            kit_path.mkdir(parents=True)
            for item in temp_dir.iterdir():
                shutil.move(str(item), str(kit_path))

            # Get metadata
            stats = kit_path.stat()
            metadata = KitMetadata(
                name=data.get('name', kit_path.parent.name),
                version=version,
                created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
                size=stats.st_size,
                owner=owner,
                doc_version=data.get('docVersion', 'v1'),
                kit_id=kit_id,
                environment=data.get('environment', [])
            )

            return metadata

        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
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
                for kit_dir in owner_dir.iterdir():
                    if kit_dir.is_dir():
                        # Iterate through version directories
                        for version_dir in kit_dir.iterdir():
                            if version_dir.is_dir():
                                metadata = self._get_metadata(version_dir)
                                if metadata:
                                    kits.append(metadata)

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



    def get_registry_kits(self) -> List[Dict[str, Any]]:
        """
        Get all kits from the registry
        
        Returns:
            List[Dict[str, Any]]: List of kit data from registry
            
        Raises:
            RegistryError: If registry connection fails
            KitError: Other errors during API call
        """
        if not (base_url := os.getenv('REGISTRY_URL')):
            raise KitError("REGISTRY_URL environment variable not set")
            
        # Construct registry URL for kits endpoint
        registry_url = urljoin(base_url, "api/registry/kits")
        
        try:
            with httpx.Client() as client:
                response = client.get(registry_url)
                response.raise_for_status()
                data = response.json()
                return data.get("kits", [])
        except httpx.HTTPError as e:
            raise RegistryError(f"Failed to get kits from registry: {str(e)}")
        except Exception as e:
            raise KitError(f"Failed to process registry response: {str(e)}")
