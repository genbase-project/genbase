from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.services.core.project import ProjectError, ProjectMetadata, ProjectService


class CreateProjectRequest(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    id: str
    name: str
    created_at: str

    @classmethod
    def from_metadata(cls, metadata: ProjectMetadata) -> "ProjectResponse":
        return cls(
            id=metadata.id,
            name=metadata.name,
            created_at=metadata.created_at
        )

class ProjectRouter:
    """FastAPI router for project management"""

    def __init__(
        self,
        project_service: ProjectService,
        prefix: str = "/project"
    ):
        """
        Initialize project router
        
        Args:
            project_service: Project service
            prefix: URL prefix for routes
        """
        self.service = project_service
        self.router = APIRouter(prefix=prefix, tags=["project"])
        self._setup_routes()

    async def _create_project(self, request: CreateProjectRequest):
        """Create project"""
        try:
            metadata = self.service.create_project(request.name)
            return ProjectResponse.from_metadata(metadata)
        except ProjectError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_project(self, project_id: str):
        """Get project by ID"""
        try:
            metadata = self.service.get_project(project_id)
            if not metadata:
                raise HTTPException(status_code=404, detail="Project not found")
            return ProjectResponse.from_metadata(metadata)
        except ProjectError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_all_projects(self):
        """Get all projects"""
        try:
            projects = self.service.get_all_projects()
            return [ProjectResponse.from_metadata(p) for p in projects]
        except ProjectError as e:
            raise HTTPException(status_code=500, detail=str(e))


    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "",
            self._create_project,
            methods=["POST"],
            response_model=ProjectResponse,
            summary="Create project"
        )

        self.router.add_api_route(
            "/{project_id}",
            self._get_project,
            methods=["GET"],
            response_model=ProjectResponse,
            summary="Get project by ID"
        )

        self.router.add_api_route(
            "",
            self._get_all_projects,
            methods=["GET"],
            response_model=List[ProjectResponse],
            summary="Get all projects"
        )
