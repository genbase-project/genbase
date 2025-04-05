from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from engine.services.core.kit import (
    InvalidVersionError,
    KitError,
    KitMetadata,
    KitNotFoundError,
    KitService,
    RegistryError,
    VersionExistsError,
    VersionSort,
)

# Pydantic models for API responses


class KitResponse(BaseModel):
    name: str
    version: str
    created_at: str
    size: int
    owner: str = "default"
    doc_version: str = "v1"
    kit_id: str = ""
    environment: List[dict] = []

    @classmethod
    def from_metadata(cls, metadata: KitMetadata) -> "KitResponse":
        return cls(
            name=metadata.name,
            version=metadata.version,
            created_at=metadata.created_at,
            size=metadata.size,
            owner=metadata.owner,
            doc_version=metadata.doc_version,
            kit_id=metadata.kit_id,
            environment=metadata.environment
        )


class KitListResponse(BaseModel):
    kits: List[KitResponse]

class KitVersionsResponse(BaseModel):
    versions: List[str]

















class RegistryKitResponse(BaseModel):
    """Pydantic model for registry kit response"""
    fileName: str
    downloadURL: str
    checksum: str
    kitConfig: dict
    uploadedAt: str


class RegistryKitsResponse(BaseModel):
    """Pydantic model for multiple registry kits response"""
    kits: List[RegistryKitResponse]



class KitRouter:
    """FastAPI router for kit management endpoints"""

    def __init__(
        self,
        kit_service: KitService,
        prefix: str = "/kit"
    ):
        """
        Initialize kit router
        
        Args:
            kit_service: Kit management service
            prefix: URL prefix for routes
        """
        self.service = kit_service
        self.router = APIRouter(prefix=prefix, tags=["kits"])
        self._setup_routes()

    async def _upload_kit(
        self,
        kit_file: UploadFile = File(...)
    ):
        """Handle kit upload"""
        try:
            metadata = self.service.save_kit(
                kit_file.file
            )

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Kit uploaded successfully",
                    "kit_info": KitResponse.from_metadata(metadata).dict()
                }
            )

        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except VersionExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_kits(self):
        """List all kits"""
        try:
            kits = self.service.get_all_kits()
            return KitListResponse(
                kits=[KitResponse.from_metadata(p) for p in kits]
            )
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_kit_versions(self, owner: str, kit_id: str):
        """List kit versions"""
        try:
            versions = self.service.get_kit_versions(owner, kit_id, sort=VersionSort.DESCENDING)
            return KitVersionsResponse(versions=versions)
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _delete_kit_version(self, owner: str, kit_id: str, version: str):
        """Delete kit version"""
        try:
            self.service.delete_kit_version(owner, kit_id, version)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Kit {kit_id} version {version} deleted successfully"
                }
            )
        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _delete_kit(self, owner: str,kit_id: str):
        """Delete kit and all versions"""
        try:
            self.service.delete_kit(owner, kit_id)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Kit {kit_id} deleted successfully"
                }
            )
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _install_kit(self, owner: str, kit_id: str, version: str = None):
        """Install kit from registry"""
        try:
            metadata = self.service.install_kit(owner, kit_id, version)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Kit installed successfully",
                    "kit_info": KitResponse.from_metadata(metadata).dict()
                }
            )
        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))




    async def _get_registry_kit_versions(self, owner: str, kit_id: str):
        """
        Get all available versions of a kit from the registry
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            
        Returns:
            JSON response with versions list
        """
        try:
            versions = self.service.get_registry_kit_versions(owner, kit_id)
            return JSONResponse(content={"versions": versions})
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RegistryError as e:
            raise HTTPException(status_code=503, detail=f"Registry error: {str(e)}")
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))



    async def _get_registry_kits(self):
        """Get all kits from registry and format them according to RegistryKitResponse"""
        try:
            # Get registry kits (already transformed to match RegistryKitResponse format)
            kits = self.service.get_registry_kits()
            
            # Create response without additional transformation
            return RegistryKitsResponse(kits=kits)
        except RegistryError as e:
            raise HTTPException(status_code=503, detail=f"Registry error: {str(e)}")
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))




    async def _upload_install_kit(
        self,
        kit_file: UploadFile = File(...)
    ):
        """Handle direct kit upload and installation"""
        try:
            metadata = self.service.save_kit(
                kit_file.file
            )

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Kit uploaded and installed successfully",
                    "kit_info": KitResponse.from_metadata(metadata).dict()
                }
            )

        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except VersionExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))
    

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/",
            self._upload_kit,
            methods=["POST"],
            summary="Upload kit"
        )


        self.router.add_api_route(
            "/upload",
            self._upload_install_kit,
            methods=["POST"],
            summary="Upload and install kit from tar.gz file"
        )

        self.router.add_api_route(
            "/install/{owner}/{kit_id}/{version}",
            self._install_kit,
            methods=["POST"],
            summary="Install kit from registry with specific version"
        )

        self.router.add_api_route(
            "/install/{owner}/{kit_id}",
            self._install_kit,
            methods=["POST"],
            summary="Install kit from registry with latest version"
        )

        self.router.add_api_route(
            "",
            self._list_kits,
            methods=["GET"],
            response_model=KitListResponse,
            summary="List all kits"
        )

        self.router.add_api_route(
            "/{owner}/{kit_id}/versions",
            self._list_kit_versions,
            methods=["GET"],
            response_model=KitVersionsResponse,
            summary="List kit versions"
        )

        self.router.add_api_route(
            "/{owner}/{kit_id}/{version}",
            self._delete_kit_version,
            methods=["DELETE"],
            summary="Delete kit version"
        )

        self.router.add_api_route(
            "/{owner}/{kit_id}",
            self._delete_kit,
            methods=["DELETE"],
            summary="Delete kit"
        )



            # Add this route in the _setup_routes method
        self.router.add_api_route(
                "/registry",
                self._get_registry_kits,
                methods=["GET"],
                response_model=RegistryKitsResponse,
                summary="Get all kits from registry"
        )




        self.router.add_api_route(
            "/registry/config/{owner}/{kit_id}/{version}",
            self._get_kit_config,
            methods=["GET"],
            summary="Get kit configuration (kit.yaml contents)"
        )
        
        # Add registry versions route using our get_registry_kit_versions implementation
        self.router.add_api_route(
            "/registry/versions/{owner}/{kit_id}",
            self._get_registry_kit_versions,
            methods=["GET"],
            summary="Get available versions of a kit from registry"
        )
        



    async def _get_kit_config(self, owner: str, kit_id: str, version: str):
        """
        Get kit configuration (kit.yaml contents) for a specific kit version
        
        Args:
            owner: Kit owner
            kit_id: Kit identifier
            version: Kit version
            
        Returns:
            JSON response with kit configuration
        """
        try:
            # Get kit config from the service
            kit_config = self.service.get_registry_kit_config(owner, kit_id, version)
            return JSONResponse(content=kit_config)
        except KitNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RegistryError as e:
            raise HTTPException(status_code=503, detail=f"Registry error: {str(e)}")
        except KitError as e:
            raise HTTPException(status_code=500, detail=str(e))