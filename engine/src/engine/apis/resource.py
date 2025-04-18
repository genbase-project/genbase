from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from sqlalchemy.orm import Session

from engine.auth.dependencies import ACT_LIST, ACT_READ, OBJ_RESOURCE, require_action
from engine.services.storage.resource import Resource, ResourceError, ResourceService
from engine.db.session import get_db

from pydantic import BaseModel
from typing import Optional

class WorkspaceFileMetadata(BaseModel):
    path: str  # Relative path within the workspace
    name: str  # File name
    mime_type: Optional[str] = None
    size: int
    last_modified: str # ISO format timestamp


class ResourceRouter:
    """FastAPI router for resource endpoints"""

    def __init__(
        self,
        resource_service: ResourceService,
        prefix: str = "/resource"
    ):
        self.service = resource_service
        self.router = APIRouter(prefix=prefix, tags=["resources"])
        self._setup_routes()












    async def _list_workspace_paths(self, module_id: str) -> List[WorkspaceFileMetadata]:
        """List all files in the module's workspace with metadata."""
        try:
            # The service now returns a list of dicts matching the model
            paths_data = self.service.list_workspace_paths(module_id)
            # Validate data with the Pydantic model
            return [WorkspaceFileMetadata(**item) for item in paths_data]
        except ResourceError as e:
            # Use 404 if it's a "not found" type error, 400/500 otherwise
            if "not found" in str(e).lower():
                 raise HTTPException(status_code=404, detail=str(e))
            else:
                 raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Catch unexpected errors
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


    # --- NEW ENDPOINT: Get Workspace File Content ---
    async def _get_workspace_file_content(
        self,
        module_id: str,
        relative_path: str = Query(..., description="Relative path of the file within the workspace")
    ) -> Response:
        """Gets the content of a specific file, handling binary types."""
        try:
            content_bytes, mime_type = self.service.get_workspace_file(module_id, relative_path)

            # Use a sensible default if MIME type detection fails
            media_type = mime_type if mime_type else "application/octet-stream"

            # Extract filename for Content-Disposition
            file_name = Path(relative_path).name

            headers = {
                # Suggest filename for download
                "Content-Disposition": f'inline; filename="{file_name}"'
                # Use 'attachment' instead of 'inline' to force download
            }

            # Return raw bytes with appropriate headers
            return Response(content=content_bytes, media_type=media_type, headers=headers)

        except ResourceError as e:
            if "not found" in str(e).lower() or "Access denied" in str(e):
                 raise HTTPException(status_code=404, detail=str(e))
            elif "Path is not a file" in str(e):
                 raise HTTPException(status_code=400, detail=str(e))
            else:
                 raise HTTPException(status_code=400, detail=str(e)) # Or 500 if it's an internal read error
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")



    async def _get_workspace_resources(self, module_id: str) -> List[Resource]:
        """Get workspace resources"""
        try:
            resources = self.service.get_workspace_resources(module_id)
            return resources
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))



    async def _get_provide_instruction_resources(self, module_id: str) -> List[Resource]:
        """Get specification resources"""
        try:
            resources = self.service.get_provided_instruction_resources(module_id)
            return resources
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))


    def _setup_routes(self):
        """Setup all routes"""


        self.router.add_api_route(
            "/{module_id}/workspace/paths",
            self._list_workspace_paths,
            methods=["GET"],
            response_model=List[WorkspaceFileMetadata],
            summary="List workspace file paths and metadata",
            # Requires LIST action on RESOURCE object
            dependencies=require_action(OBJ_RESOURCE, ACT_LIST)
        )

        self.router.add_api_route(
            "/{module_id}/workspace/file",
            self._get_workspace_file_content,
            methods=["GET"],
            summary="Get content of a specific workspace file",
            # Requires READ action on RESOURCE object
            dependencies=require_action(OBJ_RESOURCE, ACT_READ)
        )

        self.router.add_api_route(
            "/{module_id}/workspace",
            self._get_workspace_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get workspace resources",
            # Requires READ action on RESOURCE object (getting content)
            dependencies=require_action(OBJ_RESOURCE, ACT_READ)
        )

        self.router.add_api_route(
            "/{module_id}/provide-instructions",
            self._get_provide_instruction_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get Provide Instructions resources",
            # Requires READ action on RESOURCE object
            dependencies=require_action(OBJ_RESOURCE, ACT_READ)
        )