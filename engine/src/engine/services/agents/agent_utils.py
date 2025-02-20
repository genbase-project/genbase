import subprocess
from typing import Tuple
from pathlib import Path
from typing import Dict, Optional, List
from engine.services.core.module import ModuleService
from engine.services.storage.repository import RepoService
from engine.services.agents.code_edit import CodeEdit, CodeEditResult, CodeBlockEditUtil
from loguru import logger
from directory_tree import DisplayTree

class AgentUtils:
    """Utility class for common agent operations"""

    def __init__(self, module_service: ModuleService, repo_service: RepoService, module_id: str, workflow: str):
        """
        Initialize AgentUtils for a specific module and workflow
        
        Args:
            module_service: Module service instance
            repo_service: Repository service instance
            module_id: Module ID this utils instance is for
            workflow: Workflow name this utils instance is for
        """
        self.module_service = module_service
        self.repo_service = repo_service
        self.module_id = module_id
        self.workflow = workflow

        # Get module metadata to access repo info
        self.module_metadata = self.module_service.get_module_metadata(module_id)
        self.repo_path = self.repo_service.get_repo_path(self.module_metadata.repo_name)

    def read_file(self, relative_path: str) -> Optional[str]:
        """
        Read contents of a file relative to the repository root
        
        Args:
            relative_path: Path relative to repository root
            
        Returns:
            str: File contents or None if file doesn't exist
            
        Raises:
            Exception: On read errors
        """
        try:
            file_path = Path(self.repo_path) / relative_path

            logger.debug(f"Reading file: {file_path}")
            if not file_path.exists():
                return None
                
            return file_path.read_text()
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {str(e)}")
            raise

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
            List[Path]: List of Path objects for all files in the directory
                
        Raises:
            Exception: On directory access errors
        """
        try:
            dir_path = Path(self.repo_path) / relative_path
            if not dir_path.exists():
                logger.error(f"Directory does not exist: {dir_path}")
                return []
                
            return [p for p in dir_path.rglob("*") if p.is_file()]
        except Exception as e:
            logger.error(f"Error listing files in {relative_path}: {str(e)}")
            raise


    def apply_code_changes(self, file_path: str, edits: List[Dict[str,str]]) -> CodeEditResult:
        """
        Apply multiple code edits to a file and return the result
        
        Args:
            file_path: Path to file relative to repository root
            edits: List of edits to apply, each with original/updated content
            
        Returns:
            CodeEditResult containing:
            - success: Whether all edits were applied successfully 
            - content: Modified content if successful
            - error: Error message if failed
            - similar: Similar blocks found if no exact match
            
        Example:
            edits = [{
                "original":"def old_code():", 
                "updated":"def new_code():"
            }]
            result = utils.apply_code_changes("src/file.py", edits)
        """
        try:
            abs_path = Path(self.repo_path) / file_path
            content = abs_path.read_text() if abs_path.exists() else ""
            edits = [CodeEdit(**edit) for edit in edits]
            editor = CodeBlockEditUtil()
            result = editor.apply_edits(content, edits)

                
            return result
            
        except Exception as e:
            logger.error(f"Error applying code changes to {file_path}: {str(e)}")
            return CodeEditResult(success=False, error=str(e))


    def get_repo_tree(self, path: Optional[Path]) -> str:
        """
        Get the repository tree

        args:

            path: Optional path to get tree for
            
        """
        if path:
            return DisplayTree(
                dir_path=path,
            )

        return DisplayTree(
         dir_path=self.repo_path,
        )












    def execute_cmd(self, command: str, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Execute a CLI command
        
        Args:
            command: Command to execute
            cwd: Working directory for command execution. Defaults to repo root
            
        Returns:
            Tuple[bool, str, str]: (success, output, error)
            - success: Whether command executed successfully
            - output: stdout from command
            - error: stderr from command
                
        Raises:
            Exception: On command execution errors
        """
        try:
            # Default to repo root if no working directory specified
            working_dir = cwd if cwd else self.repo_path

            # Execute command
            logger.debug(f"Executing command: {command} in {working_dir}")
            process = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                shell=True  # Allows command to be passed as a string
            )

            return (
                process.returncode == 0,
                process.stdout,
                process.stderr
            )

        except Exception as e:
            logger.error(f"Error executing command {command}: {str(e)}")
            return False, "", str(e)