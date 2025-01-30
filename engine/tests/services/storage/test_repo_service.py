# tests/services/storage/test_repo_service.py
import io
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from engine.services.storage.repository import (
    RepoService, RepoNotFoundError, RepoExistsError, CommitInfo
)

@pytest.fixture
def repo_service(temp_dir):
    return RepoService(
        base_path=temp_dir / "repos",
        search_index_path=temp_dir / "indices"
    )

@pytest.fixture
def sample_file():
    content = io.BytesIO(b"test content")
    return content

@pytest.fixture
def mock_extract_func():
    return Mock()

def test_create_repository(repo_service, sample_file, mock_extract_func):
    """Test repository creation"""
    result = repo_service.create_repository(
        repo_name="test-repo",
        content_file=sample_file,
        filename="test.txt",
        extract_func=mock_extract_func
    )
    
    assert result["repo_name"] == "test-repo"
    assert result["status"] == "success"
    assert (repo_service.base_path / "test-repo").exists()

def test_create_existing_repository(repo_service, sample_file, mock_extract_func):
    """Test creating repository that already exists"""
    repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)
    
    with pytest.raises(RepoExistsError):
        repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)

def test_list_repositories(repo_service, sample_file, mock_extract_func):
    """Test listing repositories"""
    repo_service.create_repository("repo1", sample_file, "test.txt", mock_extract_func)
    repo_service.create_repository("repo2", sample_file, "test.txt", mock_extract_func)
    
    repos = repo_service.list_repositories()
    assert len(repos) == 2
    assert "repo1" in repos
    assert "repo2" in repos

def test_list_files(repo_service, sample_file, mock_extract_func):
    """Test listing files in repository"""
    repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)
    
    files = repo_service.list_files("test-repo")
    assert "test.txt" in files

def test_list_files_nonexistent_repo(repo_service):
    """Test listing files in non-existent repository"""
    with pytest.raises(RepoNotFoundError):
        repo_service.list_files("nonexistent-repo")

def test_delete_repository(repo_service, sample_file, mock_extract_func):
    """Test repository deletion"""
    repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)
    
    repo_service.delete_repository("test-repo")
    assert not (repo_service.base_path / "test-repo").exists()

def test_delete_nonexistent_repository(repo_service):
    """Test deleting non-existent repository"""
    with pytest.raises(RepoNotFoundError):
        repo_service.delete_repository("nonexistent-repo")

def test_commit_changes(repo_service, sample_file, mock_extract_func):
    """Test committing changes"""
    # Create repository with initial content
    repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)
    
    # Make some changes
    repo_path = repo_service._get_repo_path("test-repo")
    (repo_path / "new_file.txt").write_text("new content")
    
    commit_info = CommitInfo(
        commit_message="Test commit",
        author_name="Test Author",
        author_email="test@example.com"
    )
    
    result = repo_service.commit_changes("test-repo", commit_info)
    assert result["status"] == "success"
    assert result["committed"] is True
    assert "commit_hash" in result



def test_update_file_invalid_path(repo_service, sample_file, mock_extract_func):
    """Test updating file with invalid path"""
    repo_service.create_repository("test-repo", sample_file, "test.txt", mock_extract_func)
    
    def mock_validator(repo_path, file_path):
        return False
    
    with pytest.raises(Exception, match="Invalid file path"):
        repo_service.update_file(
            repo_name="test-repo",
            file_path="../test.txt",
            content="updated content",
            path_validator=mock_validator
        )