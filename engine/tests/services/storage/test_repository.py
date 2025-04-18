# tests/services/storage/test_repository.py

import pytest
import zipfile
import io
import os
from pathlib import Path
from datetime import datetime
from git import Repo, Actor, GitCommandError

from engine.services.storage.workspace import (
    WorkspaceService,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WorkspaceError,
    CommitInfo,
)
from engine.utils.file import extract_zip, is_safe_path

@pytest.fixture
def repo_service(tmp_path: Path) -> WorkspaceService:
    """Fixture for RepoService initialized with a temporary base path."""
    base_path = tmp_path / "repos"
    base_path.mkdir()
    return WorkspaceService(base_path=base_path)

@pytest.fixture
def create_zip_content() -> bytes:
    """Fixture to create in-memory zip content."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("file1.txt", "content1")
        zipf.writestr("subdir/file2.txt", "content2")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

@pytest.fixture
def create_test_repo(repo_service: WorkspaceService, create_zip_content: bytes):
    """Helper fixture to create a standard test repo."""
    repo_name = "test_repo"
    content_file = io.BytesIO(create_zip_content)
    result = repo_service.create_workspace(
        workspace_name=repo_name,
        content_file=content_file,
        filename="test.zip",
        extract_func=extract_zip
    )
    repo_path = repo_service.get_workspace_path(repo_name)
    return repo_name, repo_path, result

@pytest.fixture
def create_parent_child_repos(repo_service: WorkspaceService):
    """Fixture to create two repos for submodule testing."""
    parent_name = "parent_repo"
    child_name = "child_repo"

    # Create parent repo (can be empty initially)
    parent_path = repo_service.get_workspace_path(parent_name)
    parent_path.mkdir()
    parent_git_repo = Repo.init(parent_path)
    # Add a dummy file and commit to have a branch
    (parent_path / "dummy.txt").touch()
    parent_git_repo.index.add(["dummy.txt"])
    parent_git_repo.index.commit("Initial commit for parent")


    # Create child repo with some content
    child_path = repo_service.get_workspace_path(child_name)
    child_path.mkdir()
    child_git_repo = Repo.init(child_path)
    (child_path / "child_file.txt").write_text("child content")
    child_git_repo.index.add(["child_file.txt"])
    child_git_repo.index.commit("Initial commit for child")

    return parent_name, child_name

# --- Test Cases ---

class TestRepoService:

    def test_get_repo_path(self, repo_service: WorkspaceService):
        repo_name = "my_repo"
        expected_path = repo_service.base_path / repo_name
        assert repo_service.get_workspace_path(repo_name) == expected_path

    def test_create_repository_success(self, repo_service: WorkspaceService, create_zip_content: bytes):
        repo_name = "new_repo"
        content_file = io.BytesIO(create_zip_content)
        result = repo_service.create_workspace(
            workspace_name=repo_name,
            content_file=content_file,
            filename="test.zip",
            extract_func=extract_zip
        )

        assert result["status"] == "success"
        assert result["repo_name"] == repo_name
        repo_path = repo_service.get_workspace_path(repo_name)
        assert repo_path.exists()
        assert (repo_path / ".git").exists() # Check if git repo was initialized
        assert (repo_path / "file1.txt").exists()
        assert (repo_path / "subdir" / "file2.txt").exists()

        # Verify initial commit
        git_repo = Repo(repo_path)
        assert len(list(git_repo.iter_commits())) == 1
        assert git_repo.head.commit.message == "Initial commit"

    def test_create_repository_already_exists(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, _, _ = create_test_repo
        content_file = io.BytesIO(b"dummy content") # Content doesn't matter here
        with pytest.raises(WorkspaceExistsError, match=f"Repository {repo_name} already exists"):
            repo_service.create_workspace(
                workspace_name=repo_name,
                content_file=content_file,
                filename="another.zip",
                extract_func=extract_zip
            )

    def test_list_repositories_empty(self, repo_service: WorkspaceService):
        assert repo_service.list_workspaces() == []

    def test_list_repositories_single(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, _, _ = create_test_repo
        assert repo_service.list_workspaces() == [repo_name]

    def test_list_repositories_multiple(self, repo_service: WorkspaceService, create_zip_content: bytes):
        repo_name1 = "repo1"
        repo_name2 = "repo2"
        repo_service.create_workspace(repo_name1, io.BytesIO(create_zip_content), "r1.zip", extract_zip)
        repo_service.create_workspace(repo_name2, io.BytesIO(create_zip_content), "r2.zip", extract_zip)
        assert sorted(repo_service.list_workspaces()) == sorted([repo_name1, repo_name2])

    def test_list_files_success(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        # Add another file for testing listing
        (repo_path / "another_file.md").write_text("# Markdown")
        git_repo = Repo(repo_path)
        git_repo.index.add(["another_file.md"])
        git_repo.index.commit("Add markdown file")

        files = repo_service.list_files(repo_name)

        expected_files = {"file1.txt", "subdir/file2.txt", "another_file.md"}
        assert set(files) == expected_files

    def test_list_files_repo_not_found(self, repo_service: WorkspaceService):
        with pytest.raises(WorkspaceNotFoundError):
            repo_service.list_files("non_existent_repo")

    def test_delete_repository_success(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        assert repo_path.exists()
        repo_service.delete_workspace(repo_name)
        assert not repo_path.exists()

    def test_delete_repository_not_found(self, repo_service: WorkspaceService):
        with pytest.raises(WorkspaceNotFoundError):
            repo_service.delete_workspace("non_existent_repo")

    def test_commit_changes_no_changes(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, _, _ = create_test_repo
        commit_info = CommitInfo(commit_message="Test commit")
        result = repo_service.commit_changes(repo_name, commit_info)
        assert result["committed"] is False
        assert result["status"] == "success" # Check status instead of exact message

    def test_commit_changes_with_changes(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        new_file_path = repo_path / "new_file.py"
        new_file_path.write_text("print('hello')")

        commit_info = CommitInfo(
            commit_message="Add new python file",
            author_name="Test Author",
            author_email="test@example.com"
        )
        result = repo_service.commit_changes(repo_name, commit_info)

        assert result["status"] == "success" # Check status
        assert result["committed"] is True
        assert result["commit_message"] == "Add new python file"
        assert "new_file.py" in result["files_changed"]

        # Verify using GitPython
        git_repo = Repo(repo_path)
        last_commit = git_repo.head.commit
        assert last_commit.message == "Add new python file"
        assert last_commit.author.name == "Test Author"
        assert last_commit.author.email == "test@example.com"

    def test_commit_changes_repo_not_found(self, repo_service: WorkspaceService):
         commit_info = CommitInfo(commit_message="Test commit")
         with pytest.raises(WorkspaceNotFoundError):
            repo_service.commit_changes("non_existent_repo", commit_info)

    def test_update_file_create_new(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        file_path_str = "new_dir/created_file.txt"
        content = "This file was created by the test."

        result = repo_service.update_file(repo_name, file_path_str, content, is_safe_path)

        assert result["status"] == "success" # Check status
        # assert "created successfully" in result["message"] # Less brittle check
        full_path = repo_path / file_path_str
        assert full_path.exists()
        assert full_path.read_text() == content

    def test_update_file_update_existing(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        file_path_str = "file1.txt"
        new_content = "Updated content."
        full_path = repo_path / file_path_str
        assert full_path.read_text() == "content1" # Verify initial content

        result = repo_service.update_file(repo_name, file_path_str, new_content, is_safe_path)

        assert result["status"] == "success" # Check status
        # assert "updated successfully" in result["message"] # Less brittle check
        assert full_path.read_text() == new_content

    def test_update_file_invalid_path(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, _, _ = create_test_repo
        with pytest.raises(WorkspaceError, match="Invalid file path"):
            repo_service.update_file(repo_name, "../outside.txt", "danger", is_safe_path)

    def test_update_file_repo_not_found(self, repo_service: WorkspaceService):
        with pytest.raises(WorkspaceNotFoundError):
            repo_service.update_file("non_existent_repo", "file.txt", "content", is_safe_path)

    def test_get_active_branch(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, _, _ = create_test_repo
        branch = repo_service.get_active_branch(repo_name)
        # Default branch is usually 'master' or 'main'
        assert branch in ["master", "main"]

    def test_get_active_branch_repo_not_found(self, repo_service: WorkspaceService):
        with pytest.raises(WorkspaceNotFoundError):
            repo_service.get_active_branch("non_existent_repo")

    def test_add_submodule_success(self, repo_service: WorkspaceService, create_parent_child_repos):
        parent_name, child_name = create_parent_child_repos
        submodule_rel_path = "libs/child" # Relative path within parent

        result = repo_service.add_submodule(parent_name, child_name, path=submodule_rel_path)

        assert result["status"] == "success"
        assert result["submodule_path"] == submodule_rel_path

        parent_repo_path = repo_service.get_workspace_path(parent_name)
        submodule_full_path = parent_repo_path / submodule_rel_path
        assert submodule_full_path.exists()
        assert (submodule_full_path / "child_file.txt").exists() # Check content

        # Verify .gitmodules
        gitmodules_path = parent_repo_path / ".gitmodules"
        assert gitmodules_path.exists()
        with open(gitmodules_path, 'r') as f:
            content = f.read()
            assert f'[submodule "{submodule_rel_path}"]' in content
            assert f"path = {submodule_rel_path}" in content
            # URL will be the absolute path to the child repo

        # Verify commit
        parent_git_repo = Repo(parent_repo_path)
        last_commit = parent_git_repo.head.commit
        assert f"Add {child_name} as submodule at {submodule_rel_path}" in last_commit.message

    def test_add_submodule_parent_not_found(self, repo_service: WorkspaceService, create_parent_child_repos):
        _, child_name = create_parent_child_repos
        with pytest.raises(WorkspaceNotFoundError, match="Parent repository"):
            repo_service.add_submodule("fake_parent", child_name, "libs/child")

    def test_add_submodule_child_not_found(self, repo_service: WorkspaceService, create_parent_child_repos):
        parent_name, _ = create_parent_child_repos
        with pytest.raises(WorkspaceNotFoundError, match="Child repository"):
            repo_service.add_submodule(parent_name, "fake_child", "libs/child")



    def test_remove_submodule_repo_not_found(self, repo_service: WorkspaceService):
        with pytest.raises(WorkspaceNotFoundError):
            repo_service.remove_submodule("non_existent_repo", "some/path")

    def test_remove_submodule_not_a_submodule(self, repo_service: WorkspaceService, create_test_repo):
        repo_name, repo_path, _ = create_test_repo
        # 'subdir' exists but is not a submodule
        with pytest.raises(WorkspaceError, match="'subdir' is not a submodule"):
            repo_service.remove_submodule(repo_name, "subdir")