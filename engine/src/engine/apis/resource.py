from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from engine.services.storage.resource import Resource, ResourceError, ResourceService
from engine.db.session import get_db


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

    async def _generate_manifest(
        self,
        module_id: str,
        db: Session = Depends(get_db)
    ) -> Resource:
        """Generate a new work manifest"""
        try:
            manifest = await self.service.generate_work_manifest(module_id, db)
            return manifest
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_manifests(
        self,
        module_id: str,
        db: Session = Depends(get_db)
    ) -> List[Resource]:
        """Get all work manifests"""
        try:
            manifests = self.service.get_manifest_resources(module_id, db)
            return manifests
        except ResourceError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""

        # Add manifest routes
        self.router.add_api_route(
            "/{module_id}/manifest",
            self._generate_manifest,
            methods=["GET"],
            response_model=Resource,
            summary="Generate new work manifest"
        )

        self.router.add_api_route(
            "/{module_id}/manifests",
            self._get_manifests,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get all work manifests"
        )
        self.router.add_api_route(
            "/{module_id}/workspace",
            self._get_workspace_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get workspace resources"
        )

        self.router.add_api_route(
            "/{module_id}/provide-instructions",
            self._get_provide_instruction_resources,
            methods=["GET"],
            response_model=List[Resource],
            summary="Get Provide Instructions resources"
        )
