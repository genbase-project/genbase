from typing import List

from fastapi import APIRouter, HTTPException

from engine.services.storage.resource import Resource, ResourceError, ResourceService


class ResourceRouter:
    """FastAPI router for resource endpoints"""

    def __init__(
        self,
        resource_service: ResourceService,
        prefix: str = "/resources"
    ):
        self.service = resource_service
        self.router = APIRouter(prefix=prefix, tags=["resources"])
        self._setup_routes()

    async def _get_workspace_resources(self, module_id: str) -> List[Resource]:
        """Get workspace resources"""
        try:
            resources = self.service.get_workspace_resources(module_id)
            return resources
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_documentation_resources(self, module_id: str) -> List[Resource]:
        """Get documentation resources"""
        try:
            resources = self.service.get_documentation_resources(module_id)
            return resources
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_specification_resources(self, module_id: str) -> List[Resource]:
        """Get specification resources"""
        try:
            resources = self.service.get_specification_resources(module_id)
            return resources
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/{module_id}/workspace",
            self._get_workspace_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get workspace resources"
        )

        self.router.add_api_route(
            "/{module_id}/documentation",
            self._get_documentation_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get documentation resources"
        )

        self.router.add_api_route(
            "/{module_id}/specification",
            self._get_specification_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get specification resources"
        )
