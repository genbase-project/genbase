from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from engine.auth.dependencies import ACT_CREATE, ACT_DELETE, ACT_LIST, ACT_READ, ACT_UPDATE, OBJ_WORKSPACE, require_action
from engine.services.storage.workspace import (
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
    workspace_name: str
    created_at: str
    status: str

class WorkspaceRouter:
    """FastAPI router for workspace management endpoints"""

    def __init__(
        self,
        workspace_service: WorkspaceService,
        prefix: str = "/workspace"
    ):
        """
        Initialize workspace router
        
        Args:
            workspace_service: Workspace service instance
            prefix: URL prefix for routes
        """
        self.service = workspace_service
        self.router = APIRouter(prefix=prefix, tags=["workspace"])
        self._setup_routes()

    async def _create_workspace(
        self,
        workspace_file: UploadFile = File(...),
        workspace_name: str = Form(...)
    ):
        """Handle workspace creation"""
        try:
            result = self.service.create_workspace(
                workspace_name=workspace_name,
                content_file=workspace_file.file,
                filename=workspace_file.filename,
                extract_func=extract_zip  # You'll need to import this
            )
            return WorkspaceCreationResponse(**result)

        except WorkspaceExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_workspaces(self):
        """List all workspaces"""
        try:
            workspaces = self.service.list_workspaces()
            return {"workspaces": workspaces}
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_workspace_files(self, workspace_name: str):
        """List workspace files"""
        try:
            files = self.service.list_files(workspace_name)
            return {"files": files}
        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _delete_workspace(self, workspace_name: str):
        """Delete workspace"""
        try:
            self.service.delete_workspace(workspace_name)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Workspace {workspace_name} deleted successfully"
                }
            )
        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _commit_changes(
        self,
        workspace_name: str,
        commit_data: CommitRequest
    ):
        """Handle workspace commit"""
        try:
            commit_info = CommitInfo(
                commit_message=commit_data.commit_message,
                author_name=commit_data.author_name,
                author_email=commit_data.author_email
            )

            result = self.service.commit_changes(workspace_name, commit_info)
            return JSONResponse(content=result)

        except WorkspaceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except WorkspaceError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _update_file(
        self,
        workspace_name: str,
        file_path: str,
        update: FileUpdateRequest
    ):
        """Handle file update"""
        try:
            result = self.service.update_file(
                workspace_name=workspace_name,
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
            self._create_workspace,
            methods=["POST"],
            response_model=WorkspaceCreationResponse,
            summary="Create new workspace",
            dependencies=require_action(OBJ_WORKSPACE, ACT_CREATE)
        )

        self.router.add_api_route(
            "/list",
            self._list_workspaces,
            methods=["GET"],
            summary="List all workspaces",
            dependencies=require_action(OBJ_WORKSPACE, ACT_LIST)
        )

        self.router.add_api_route(
            "/{workspace_name}/files",
            self._list_workspace_files,
            methods=["GET"],
            summary="List workspace files",
            # Listing files *within* a workspace implies reading it
            dependencies=require_action(OBJ_WORKSPACE, ACT_READ)
        )

        self.router.add_api_route(
            "/{workspace_name}",
            self._delete_workspace,
            methods=["DELETE"],
            summary="Delete workspace",
            dependencies=require_action(OBJ_WORKSPACE, ACT_DELETE)
        )

        self.router.add_api_route(
            "/{workspace_name}/commit",
            self._commit_changes,
            methods=["POST"],
            summary="Commit changes",
            # Committing changes is a form of updating the workspace
            dependencies=require_action(OBJ_WORKSPACE, ACT_UPDATE)
        )

        self.router.add_api_route(
            "/{workspace_name}/file",
            self._update_file,
            methods=["PUT"],
            summary="Update file",
            # Updating a file is a form of updating the workspace
            dependencies=require_action(OBJ_WORKSPACE, ACT_UPDATE)
        )
