from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from engine.auth.dependencies import ACT_CREATE, ACT_DELETE, ACT_LIST, ACT_READ, ACT_UPDATE, OBJ_REPOSITORY, require_action
from engine.services.storage.repository import (
    CommitInfo,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WorkspaceService,
    WorkspaceError,
)
from engine.utils.file import extract_zip, is_safe_path


# Pydantic models
class FileUpdateRequest(BaseModel):
    content: str

class CommitRequest(BaseModel):
    commit_message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None

class MatchPositionResponse(BaseModel):
    line_number: int
    start_char: int
    end_char: int
    line_content: str
    score: float

class SearchResponse(BaseModel):
    file_path: str
    matches: List[MatchPositionResponse]
    total_matches: int
    file_score: float

class WorkspaceCreationResponse(BaseModel):
    repo_name: str
    created_at: str
    status: str

class WorkspaceRouter:
    """FastAPI router for repository management endpoints"""

    def __init__(
        self,
        repo_service: WorkspaceService,
        prefix: str = "/repo"
    ):
        """
        Initialize repository router
        
        Args:
            repo_service: Repository service instance
            prefix: URL prefix for routes
        """
        self.service = repo_service
        self.router = APIRouter(prefix=prefix, tags=["repository"])
        self._setup_routes()

    async def _create_repo(
        self,
        repo_file: UploadFile = File(...),
        repo_name: str = Form(...)
    ):
        """Handle repository creation"""
        try:
            result = self.service.create_workspace(
                workspace_name=repo_name,
                content_file=repo_file.file,
                filename=repo_file.filename,
                extract_func=extract_zip  # You'll need to import this
            )
            return WorkspaceCreationResponse(**result)

        except WorkspaceExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_repos(self):
        """List all workspaces"""
        try:
            repos = self.service.list_repositories()
            return {"repositories": repos}
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_repo_files(self, repo_name: str):
        """List repository files"""
        try:
            files = self.service.list_files(repo_name)
            return {"files": files}
        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _delete_repo(self, repo_name: str):
        """Delete repository"""
        try:
            self.service.delete_workspace(repo_name)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Repository {repo_name} deleted successfully"
                }
            )
        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _commit_changes(
        self,
        repo_name: str,
        commit_data: CommitRequest
    ):
        """Handle repository commit"""
        try:
            commit_info = CommitInfo(
                commit_message=commit_data.commit_message,
                author_name=commit_data.author_name,
                author_email=commit_data.author_email
            )

            result = self.service.commit_changes(repo_name, commit_info)
            return JSONResponse(content=result)

        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _update_file(
        self,
        repo_name: str,
        file_path: str,
        update: FileUpdateRequest
    ):
        """Handle file update"""
        try:
            result = self.service.update_file(
                workspace_name=repo_name,
                file_path=file_path,
                content=update.content,
                path_validator=is_safe_path  # You'll need to import this
            )
            return JSONResponse(content=result)

        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _setup_routes(self):
        """Setup all routes with specific permissions."""
        self.router.add_api_route(
            "/create",
            self._create_repo,
            methods=["POST"],
            response_model=WorkspaceCreationResponse,
            summary="Create new repository",
            dependencies=require_action(OBJ_REPOSITORY, ACT_CREATE)
        )

        self.router.add_api_route(
            "/list",
            self._list_repos,
            methods=["GET"],
            summary="List all repositories",
            dependencies=require_action(OBJ_REPOSITORY, ACT_LIST)
        )

        self.router.add_api_route(
            "/{repo_name}/files",
            self._list_repo_files,
            methods=["GET"],
            summary="List repository files",
            # Listing files *within* a repo implies reading it
            dependencies=require_action(OBJ_REPOSITORY, ACT_READ)
        )

        self.router.add_api_route(
            "/{repo_name}",
            self._delete_repo,
            methods=["DELETE"],
            summary="Delete repository",
            dependencies=require_action(OBJ_REPOSITORY, ACT_DELETE)
        )

        self.router.add_api_route(
            "/{repo_name}/commit",
            self._commit_changes,
            methods=["POST"],
            summary="Commit changes",
            # Committing changes is a form of updating the repo
            dependencies=require_action(OBJ_REPOSITORY, ACT_UPDATE)
        )

        self.router.add_api_route(
            "/{repo_name}/file",
            self._update_file,
            methods=["PUT"],
            summary="Update file",
            # Updating a file is a form of updating the repo
            dependencies=require_action(OBJ_REPOSITORY, ACT_UPDATE)
        )
