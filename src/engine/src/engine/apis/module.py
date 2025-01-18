from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel

from engine.services.module import (
    ModuleService,
    ModuleMetadata,
    ModuleError,
    ModuleNotFoundError,
    VersionExistsError,
    InvalidVersionError,
    VersionSort
)

# Pydantic models for API responses


class ModuleResponse(BaseModel):
    name: str
    version: str
    created_at: str
    size: int
    owner: str = "default"
    doc_version: str = "v1"
    module_id: str = ""
    environment: List[dict] = []
    
    @classmethod
    def from_metadata(cls, metadata: ModuleMetadata) -> "ModuleResponse":
        return cls(
            name=metadata.name,
            version=metadata.version,
            created_at=metadata.created_at,
            size=metadata.size,
            owner=metadata.owner,
            doc_version=metadata.doc_version,
            module_id=metadata.module_id,
            environment=metadata.environment
        )
    

class ModuleListResponse(BaseModel):
    modules: List[ModuleResponse]

class ModuleVersionsResponse(BaseModel):
    versions: List[str]

class ModuleRouter:
    """FastAPI router for module management endpoints"""
    
    def __init__(
        self, 
        module_service: ModuleService,
        prefix: str = "/modules"
    ):
        """
        Initialize module router
        
        Args:
            module_service: Module management service
            prefix: URL prefix for routes
        """
        self.service = module_service
        self.router = APIRouter(prefix=prefix, tags=["modules"])
        self._setup_routes()
    
    async def _upload_module(
        self,
        module_file: UploadFile = File(...)
    ):
        """Handle module upload"""
        try:
            metadata = self.service.save_module( 
                module_file.file
            )
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module uploaded successfully",
                    "module_info": ModuleResponse.from_metadata(metadata).dict()
                }
            )
            
        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except VersionExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _list_modules(self):
        """List all modules"""
        try:
            modules = self.service.get_all_modules()
            return ModuleListResponse(
                modules=[ModuleResponse.from_metadata(p) for p in modules]
            )
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _list_module_versions(self, owner: str, module_id: str):
        """List module versions"""
        try:
            versions = self.service.get_module_versions(owner, module_id, sort=VersionSort.DESCENDING)
            return ModuleVersionsResponse(versions=versions)
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _delete_module_version(self, owner: str, module_id: str, version: str):
        """Delete module version"""
        try:
            self.service.delete_module_version(owner, module_id, version)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module {module_id} version {version} deleted successfully"
                }
            )
        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _delete_module(self, owner: str,module_id: str):
        """Delete module and all versions"""
        try:
            self.service.delete_module(owner, module_id)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module {module_id} deleted successfully"
                }
            )
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/",
            self._upload_module,
            methods=["POST"],
            summary="Upload module"
        )
        
        self.router.add_api_route(
            "",
            self._list_modules,
            methods=["GET"],
            response_model=ModuleListResponse,
            summary="List all modules"
        )
        
        self.router.add_api_route(
            "/{owner}/{module_id}/versions",
            self._list_module_versions,
            methods=["GET"],
            response_model=ModuleVersionsResponse,
            summary="List module versions"
        )
        
        self.router.add_api_route(
            "/{owner}/{module_id}/{version}",
            self._delete_module_version,
            methods=["DELETE"],
            summary="Delete module version"
        )
        
        self.router.add_api_route(
            "/{owner}/{module_id}",
            self._delete_module,
            methods=["DELETE"],
            summary="Delete module"
        )