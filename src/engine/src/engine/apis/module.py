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
    
    @classmethod
    def from_metadata(cls, metadata: ModuleMetadata) -> "ModuleResponse":
        return cls(
            name=metadata.name,
            version=metadata.version,
            created_at=metadata.created_at,
            size=metadata.size
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
        module_name: str,
        version: str,
        module_file: UploadFile = File(...)
    ):
        """Handle module upload"""
        try:
            metadata = self.service.save_module(
                module_name,
                version, 
                module_file.file
            )
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module {module_name} version {version} uploaded successfully",
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
    
    async def _list_module_versions(self, module_name: str):
        """List module versions"""
        try:
            versions = self.service.get_module_versions(module_name)
            return ModuleVersionsResponse(versions=versions)
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _delete_module_version(self, module_name: str, version: str):
        """Delete module version"""
        try:
            self.service.delete_module_version(module_name, version)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module {module_name} version {version} deleted successfully"
                }
            )
        except InvalidVersionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _delete_module(self, module_name: str):
        """Delete module and all versions"""
        try:
            self.service.delete_module(module_name)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Module {module_name} deleted successfully"
                }
            )
        except ModuleNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/{module_name}/{version}",
            self._upload_module,
            methods=["POST"],
            summary="Upload module version"
        )
        
        self.router.add_api_route(
            "",
            self._list_modules,
            methods=["GET"],
            response_model=ModuleListResponse,
            summary="List all modules"
        )
        
        self.router.add_api_route(
            "/{module_name}",
            self._list_module_versions,
            methods=["GET"],
            response_model=ModuleVersionsResponse,
            summary="List module versions"
        )
        
        self.router.add_api_route(
            "/{module_name}/{version}",
            self._delete_module_version,
            methods=["DELETE"],
            summary="Delete module version"
        )
        
        self.router.add_api_route(
            "/{module_name}",
            self._delete_module,
            methods=["DELETE"],
            summary="Delete module"
        )