import re
import shutil
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

from git import Actor, GitCommandError, Repo
from git.repo import Repo
from loguru import logger


@dataclass
class CommitInfo:
    commit_message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None

@dataclass
class MatchPosition:
    line_number: int
    start_char: int
    end_char: int
    line_content: str
    score: float

@dataclass
class SearchResult:
    file_path: str
    matches: List[MatchPosition]
    total_matches: int
    file_score: float

class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass

class RepoNotFoundError(RepositoryError):
    """Repository not found"""
    pass

class RepoExistsError(RepositoryError):
    """Repository already exists"""
    pass

class RepoService:
    """Service for managing Git repositories"""

    def __init__(
        self,
        base_path: str | Path
    ):
        """
        Initialize repository service
        
        Args:
            base_path: Base directory for storing repositories
            create_index_func: Function to create search index
        """
        self.base_path = Path(base_path)


        # Create necessary directories
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, repo_name: str) -> Path:
        """Get repository path"""
        return self.base_path / repo_name



    def _init_git_repo(self, repo_path: Path) -> Repo:
        """Initialize git repository with default configuration"""
        repo = Repo.init(repo_path)

        with repo.config_writer() as git_config:
            if not git_config.has_section('core'):
                git_config.add_section('core')
            git_config.set_value('core', 'worktree', str(repo_path.absolute()).replace('\\', '/'))

            if not git_config.has_section('user'):
                git_config.add_section('user')
            git_config.set_value('user', 'name', 'Genbase Agent')
            git_config.set_value('user', 'email', 'genbase@localhost')

        return repo

    def create_repository(
        self,
        repo_name: str,
        content_file,
        filename: str,
        extract_func
    ) -> dict:
        """
        Create a new repository from uploaded content
        
        Args:
            repo_name: Name of the repository
            content_file: File-like object containing repository content
            filename: Original filename
            extract_func: Function to extract zip files
            
        Returns:
            dict: Repository creation info
            
        Raises:
            RepoExistsError: If repository already exists
        """
        repo_path = self.get_repo_path(repo_name)

        if repo_path.exists():
            raise RepoExistsError(f"Repository {repo_name} already exists")

        try:
            # Create repository directory
            repo_path.mkdir(parents=True)
            temp_file = repo_path / filename

            # Save uploaded file
            with temp_file.open("wb") as buffer:
                shutil.copyfileobj(content_file, buffer)

            # Extract if zip file
            if filename.endswith('.zip'):
                extract_func(temp_file, repo_path)
                temp_file.unlink()

            # Initialize git repository
            try:
                repo = self._init_git_repo(repo_path)
                repo.git.add(A=True)
                repo.index.commit("Initial commit")
            except Exception as e:
                print(f"Git initialization error: {str(e)}")


            return {
                "repo_name": repo_name,
                "created_at": datetime.now().isoformat(),
                "status": "success"
            }

        except Exception as e:
            if repo_path.exists():
                shutil.rmtree(repo_path)
            raise RepositoryError(f"Failed to create repository: {str(e)}")

    def list_repositories(self) -> List[str]:
        """List all repositories"""
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]


    def list_files(self, repo_name: str) -> List[str]:
        """
        List all non-hidden files in a repository, excluding the .git directory.

        Args:
            repo_name: Repository name

        Returns:
            List[str]: List of file paths relative to the repository root

        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self.get_repo_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        files = []
        # Iterate through items in the repo_path, skipping .git explicitly
        for item in repo_path.rglob("*"):
            try:
                # Check if item is within .git directory
                if '.git' == item.relative_to(repo_path).parts[0]:
                    continue
                if item.is_file(): # Keep it simple for now, list all non-.git files
                    files.append(str(item.relative_to(repo_path)))
            except ValueError:
                continue
        return files

    def delete_repository(self, repo_name: str) -> None:
        """
        Delete a repository and its search index
        
        Args:
            repo_name: Repository to delete
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self.get_repo_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        try:
            shutil.rmtree(repo_path)
        except Exception as e:
            raise RepositoryError(f"Failed to delete repository: {str(e)}")

    def commit_changes(
        self,
        repo_name: str,
        commit_info: CommitInfo
    ) -> dict:
        """
        Stage and commit changes in repository
        
        Args:
            repo_name: Repository name
            commit_info: Commit information
            
        Returns:
            dict: Commit result info
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self.get_repo_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        try:
            # Get or initialize repository
            try:
                repo = Repo(repo_path)
            except Exception:
                repo = self._init_git_repo(repo_path)

            # Check for changes
            status = repo.git.status(porcelain=True)
            if not status:
                return {
                    "status": "success",
                    "message": "No changes to commit",
                    "committed": False
                }

            # Stage changes
            repo.git.add(A=True)

            # Create commit
            author = Actor(
                commit_info.author_name or "FastAPI Git Service",
                commit_info.author_email or "fastapi@localhost"
            )

            commit = repo.index.commit(
                commit_info.commit_message,
                author=author,
                committer=author
            )

            # Get changed files
            changed_files = []
            if commit.parents:
                for diff in commit.parents[0].diff(commit):
                    if diff.a_path:
                        changed_files.append(diff.a_path)
                    if diff.b_path and diff.b_path not in changed_files:
                        changed_files.append(diff.b_path)
            else:
                changed_files = [item.path for item in commit.tree.traverse()
                               if item.type == 'blob']

            return {
                "status": "success",
                "message": "Changes committed successfully",
                "committed": True,
                "commit_hash": commit.hexsha,
                "commit_message": commit_info.commit_message,
                "files_changed": changed_files
            }

        except GitCommandError as e:
            raise RepositoryError(f"Git error: {str(e)}")
        except Exception as e:
            raise RepositoryError(f"Failed to commit changes: {str(e)}")


    def update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        path_validator
    ) -> dict:
        """
        Update file content in repository
        
        Args:
            repo_name: Repository name
            file_path: Path to file
            content: New file content
            path_validator: Function to validate file path
            
        Returns:
            dict: Update result info
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self.get_repo_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        if not path_validator(repo_path, file_path):
            raise RepositoryError("Invalid file path")

        try:
            full_file_path = (repo_path / file_path).resolve()
            full_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists
            backup_path = None
            if full_file_path.exists():
                backup_path = full_file_path.with_suffix(full_file_path.suffix + '.bak')
                shutil.copy2(full_file_path, backup_path)

            # Update file
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(content)


            # Remove backup if successful
            if backup_path and backup_path.exists():
                backup_path.unlink()

            return {
                "status": "success",
                "message": f"File {'updated' if backup_path else 'created'} successfully",
                "file_path": file_path,
                "updated_at": datetime.now().isoformat()
            }

        except Exception as e:
            # Restore from backup if exists
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, full_file_path)
                backup_path.unlink()
            raise RepositoryError(f"Failed to update file: {str(e)}")


    def get_active_branch(self, repo_name: str) -> str:
        """
        Get the default branch name of a repository
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            str: Name of the default branch (usually 'master' or 'main')
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """

        logger.info(f"Getting active branch for {repo_name}")
        repo_path = self.get_repo_path(repo_name)
        
        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")
        
            
        try:
            repo = Repo(repo_path)

            logger.info(f"Repo: {repo}")

            logger.info(f"Active branch: {repo.active_branch.name}")
            
            return repo.active_branch.name

            
        except Exception as e:
            raise RepositoryError(f"Failed to get default branch: {str(e)}")

    def add_submodule(
        self,
        parent_repo_name: str,
        child_repo_name: str,
        path: str = None,
    ) -> dict:
        """
        Add a repository as a submodule to another repository
        
        Args:
            parent_repo_name: Name of the parent repository
            child_repo_name: Name of the repository to add as a submodule
            path: Path within the parent repository where the submodule should be placed
                If None, uses the child_repo_name as the path
        
        Returns:
            dict: Result information
        
        Raises:
            RepoNotFoundError: If either repository doesn't exist
            RepositoryError: If any error occurs during the operation
        """
        parent_repo_path = self.get_repo_path(parent_repo_name)
        child_repo_path = self.get_repo_path(child_repo_name)
        
        # Validate repositories exist
        if not parent_repo_path.exists():
            raise RepoNotFoundError(f"Parent repository {parent_repo_name} not found")
        if not child_repo_path.exists():
            raise RepoNotFoundError(f"Child repository {child_repo_name} not found")
        
        # Determine submodule path
        submodule_path = path or child_repo_name
        
        try:
            # Get repository objects
            parent_repo = Repo(parent_repo_path)
            
            # Get absolute path to child repo
            child_repo_abs_path = child_repo_path.absolute()
            
            # Get default branch name
            default_branch = self.get_active_branch(child_repo_name)


            logger.info(f"Adding {child_repo_name} as submodule to {parent_repo_name} at {submodule_path}")
            
            # Add the submodule
            submodule = parent_repo.create_submodule(
                name=submodule_path,
                path=submodule_path,
                url=str(child_repo_abs_path),
                branch=default_branch
            )
            
            # Commit the change
            author = Actor("Admin", "admin@genbase")
            commit = parent_repo.index.commit(
                f"Add {child_repo_name} as submodule at {submodule_path}",
                author=author,
                committer=author
            )
            
            return {
                "status": "success",
                "message": f"Added {child_repo_name} as submodule to {parent_repo_name}",
                "parent_repo": parent_repo_name,
                "child_repo": child_repo_name,
                "submodule_path": submodule_path,
                "commit_hash": commit.hexsha
            }
            
        except GitCommandError as e:
            raise RepositoryError(f"Git error while adding submodule: {str(e)}")
        except Exception as e:
            raise RepositoryError(f"Failed to add submodule: {str(e)}")
            
    def remove_submodule(
        self,
        repo_name: str,
        submodule_path: str
    ) -> dict:
        """
        Remove a submodule from a repository
        
        Args:
            repo_name: Name of the repository containing the submodule
            submodule_path: Path to the submodule within the repository
            
        Returns:
            dict: Result information
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
            RepositoryError: If any error occurs during the operation
        """
        repo_path = self.get_repo_path(repo_name)
        
        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")
            
        full_submodule_path = (repo_path / submodule_path).resolve()
        
        if not full_submodule_path.exists():
            raise RepositoryError(f"Submodule at path '{submodule_path}' not found")
            
        try:
            repo = Repo(repo_path)
            
            # Check if it's actually a submodule
            submodules = [sm.path for sm in repo.submodules]
            if submodule_path not in submodules:
                raise RepositoryError(f"Path '{submodule_path}' is not a submodule")
                
            # 1. Deinit the submodule
            repo.git.submodule('deinit', '-f', submodule_path)
            
            # 2. Remove from .git/modules
            git_modules_path = repo_path / '.git' / 'modules' / submodule_path
            if git_modules_path.exists():
                shutil.rmtree(git_modules_path)
                
            # 3. Remove the submodule entry from .git/config
            repo.git.config('--remove-section', f'submodule.{submodule_path}', ignore_errors=True)
            
            # 4. Remove from index
            repo.git.rm('--cached', submodule_path)
            
            # 5. Commit the removal
            author = Actor("Admin", "genbase@localhost")
            commit = repo.index.commit(
                f"Remove submodule {submodule_path}",
                author=author,
                committer=author
            )
            
            # 6. Remove the submodule directory
            if full_submodule_path.exists():
                shutil.rmtree(full_submodule_path)
                
            # 7. Remove .gitmodules file if it's the last submodule
            if not repo.submodules:
                gitmodules_path = repo_path / '.gitmodules'
                if gitmodules_path.exists():
                    gitmodules_path.unlink()
                    repo.git.add('.gitmodules')
                    repo.index.commit(
                        "Remove .gitmodules file",
                        author=author,
                        committer=author
                    )
                    
            return {
                "status": "success",
                "message": f"Removed submodule {submodule_path} from {repo_name}",
                "repo_name": repo_name,
                "submodule_path": submodule_path,
                "commit_hash": commit.hexsha
            }
            
        except GitCommandError as e:
            raise RepositoryError(f"Git error while removing submodule: {str(e)}")
        except Exception as e:
            raise RepositoryError(f"Failed to remove submodule: {str(e)}")