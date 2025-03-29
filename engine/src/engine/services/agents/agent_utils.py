import subprocess
from typing import Tuple
from pathlib import Path
from typing import Dict, Optional, List
from engine.const import REPO_BASE_DIR
from engine.services.core.module import ModuleService
from engine.services.storage.repository import RepoService
from loguru import logger
from directory_tree import DisplayTree, display_tree

class AgentUtils:
    """Utility class for common agent operations"""

    def __init__(self, module_service: ModuleService, repo_service: RepoService, module_id: str, profile: str):
        """
        Initialize AgentUtils for a specific module and profile
        
        Args:
            module_service: Module service instance
            repo_service: Repository service instance
            module_id: Module ID this utils instance is for
            profile: Profile name this utils instance is for
        """
        self.module_service = module_service
        self.repo_service = repo_service
        self.module_id = module_id
        self.profile = profile

        # Get module metadata to access repo info
        self.module_metadata = self.module_service.get_module_metadata(module_id)
        self.repo_path =  REPO_BASE_DIR / self.module_metadata.repo_name

    def read_file(self, relative_path: str) -> Optional[str]:
        """
        Read contents of a file relative to the repository root.
        Skips binary files and returns None for them.
        
        Args:
            relative_path: Path relative to repository root
            
        Returns:
            str: File contents or None if file doesn't exist or is binary
        """
        try:
            file_path = Path(self.repo_path) / relative_path

            logger.debug(f"Reading file: {file_path}")
            if not file_path.exists():
                return None
                
            # Simply try to read as text and return None if it fails
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                logger.info(f"Skipping binary file: {relative_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {str(e)}")
            raise
    
    def read_files(self, relative_paths: List[str]) -> Dict[str, Optional[str]]:
        """
        Read contents of multiple files relative to the repository root
        
        Args:
            relative_paths: List of paths relative to repository root
            
        Returns:
            Dict[str, Optional[str]]: Dictionary of file contents keyed by relative path
        """
        return {path: self.read_file(path) for path in relative_paths}


    def write_file(self, relative_path: str, content: str) -> bool:
        """
        Write content to a file in the repository
        
        Args:
            relative_path: Path relative to repository root
            content: Content to write
            
        Returns:
            bool: True if successful
            
        Raises:
            Exception: On write errors
        """
        try:
            file_path = Path(self.repo_path) / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return True
        except Exception as e:
            logger.error(f"Error writing file {relative_path}: {str(e)}")
            raise


    def list_files(self, relative_path: str = "") -> List[Path]:
        """
        List all files in a directory relative to the repository root
        
        Args:
            relative_path: Path relative to repository root. If empty, lists from root
                
        Returns:
            List[Path]: List of Path objects for all files, with paths relative to repo root
                
        Raises:
            Exception: On directory access errors
        """
        try:
            dir_path = Path(self.repo_path) / relative_path
            if not dir_path.exists():
                logger.error(f"Directory does not exist: {dir_path}")
                return []
                
            # Find all files recursively
            all_files = [p for p in dir_path.rglob("*") if p.is_file()]
            
            # Convert absolute paths to paths relative to repo_path
            return [p.relative_to(self.repo_path) for p in all_files]
        except Exception as e:
            logger.error(f"Error listing files in {relative_path}: {str(e)}")
            raise
        


    def get_repo_tree(self, path: Optional[Path]=None) -> str:
        """Get the repository tree structure"""
        import os
        from pathlib import Path
        
        # Setup paths and ignore list
        if path:
            dir_path = REPO_BASE_DIR / self.module_metadata.repo_name / path
        else:
            dir_path = REPO_BASE_DIR / self.module_metadata.repo_name
            
        logger.info(f"Getting tree for repo: {dir_path}")
        
        kit = self.module_service.get_module_kit_config(self.module_id)
        ignore_list = [".git", "node_modules", ".venv", ".env", ".DS_Store", ".next", ".gitignore", ".gitmodules"]
        ignore_list.extend(kit.workspace.ignore)
        
        # Tree symbols
        symbols = {
            'space': '    ',
            'branch': '│   ',
            'tee': '├── ',
            'last': '└── '
        }
        
        # Generate tree recursively
        def _tree(path, prefix=''):
            if not os.path.isdir(path):
                return ""
                
            contents = sorted([p for p in os.listdir(path) if p not in ignore_list])
            result = ""
            
            for i, item in enumerate(contents):
                is_last = i == len(contents) - 1
                pointer = symbols['last'] if is_last else symbols['tee']
                item_path = Path(path) / item
                
                result += f"{prefix}{pointer}{item}\n"
                
                if os.path.isdir(item_path):
                    extension = symbols['space'] if is_last else symbols['branch']
                    result += _tree(item_path, prefix + extension)
                    
            return result
        
        # Generate the full tree
        tree = f"{dir_path.name}\n" + _tree(dir_path)
        logger.info(f"Tree: {tree}")
        
        return tree

