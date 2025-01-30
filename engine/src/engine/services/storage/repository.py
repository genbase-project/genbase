import re
import shutil
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

from git import Actor, GitCommandError, Repo
from git.repo import Repo


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
        base_path: str | Path,
        search_index_path: str | Path,
    ):
        """
        Initialize repository service
        
        Args:
            base_path: Base directory for storing repositories
            search_index_path: Path for storing search indices
            create_index_func: Function to create search index
        """
        self.base_path = Path(base_path)
        self.search_index_path = Path(search_index_path)


        # Create necessary directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.search_index_path.mkdir(parents=True, exist_ok=True)

    def _get_repo_path(self, repo_name: str) -> Path:
        """Get repository path"""
        return self.base_path / repo_name

    def _get_index_path(self, repo_name: str) -> Path:
        """Get search index path"""
        return self.search_index_path / repo_name

    def _init_git_repo(self, repo_path: Path) -> Repo:
        """Initialize git repository with default configuration"""
        repo = Repo.init(repo_path)

        with repo.config_writer() as git_config:
            if not git_config.has_section('core'):
                git_config.add_section('core')
            git_config.set_value('core', 'worktree', str(repo_path.absolute()).replace('\\', '/'))

            if not git_config.has_section('user'):
                git_config.add_section('user')
            git_config.set_value('user', 'name', 'FastAPI Git Service')
            git_config.set_value('user', 'email', 'fastapi@localhost')

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
        repo_path = self._get_repo_path(repo_name)

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
        List all files in a repository
        
        Args:
            repo_name: Repository name
            
        Returns:
            List[str]: List of file paths
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self._get_repo_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        files = []
        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                files.append(str(file_path.relative_to(repo_path)))

        return files

    def delete_repository(self, repo_name: str) -> None:
        """
        Delete a repository and its search index
        
        Args:
            repo_name: Repository to delete
            
        Raises:
            RepoNotFoundError: If repository doesn't exist
        """
        repo_path = self._get_repo_path(repo_name)
        index_path = self._get_index_path(repo_name)

        if not repo_path.exists():
            raise RepoNotFoundError(f"Repository {repo_name} not found")

        try:
            shutil.rmtree(repo_path)
            if index_path.exists():
                shutil.rmtree(index_path)
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
        repo_path = self._get_repo_path(repo_name)

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
        repo_path = self._get_repo_path(repo_name)

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

            # Update search index
            self.create_index(repo_path, repo_name, self.search_index_path)

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
