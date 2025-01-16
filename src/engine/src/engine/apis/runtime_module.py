from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

from engine.services.runtime_module import (
    RuntimeModuleService,
    RuntimeModuleError,
    RuntimeModuleMetadata,
    RelationType
)

# Pydantic models
class CreateModuleRequest(BaseModel):
    module_id: str
    version: str
    env_vars: Dict[str, str]

class RuntimeModuleResponse(BaseModel):
    id: str
    module_id: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str  # Changed from repo_path to repo_name
    
    @classmethod
    def from_metadata(cls, metadata: RuntimeModuleMetadata) -> "RuntimeModuleResponse":
        return cls(
            id=metadata.id,
            module_id=metadata.module_id,
            version=metadata.version,
            created_at=metadata.created_at,
            env_vars=metadata.env_vars,
            repo_name=metadata.repo_name  # Changed from repo_path to repo_name
        )

class CreateRelationRequest(BaseModel):
    source_id: str
    target_id: str
    relation_type: RelationType

class ModuleGraphResponse(BaseModel):
    nodes: List[RuntimeModuleResponse]
    edges: List[Dict]

class RuntimeModuleRouter:
    """FastAPI router for runtime module management"""
    
    def __init__(
        self,
        module_service: RuntimeModuleService,
        prefix: str = "/runtime"
    ):
        """
        Initialize runtime module router
        
        Args:
            module_service: Runtime module service
            prefix: URL prefix for routes
        """
        self.service = module_service
        self.router = APIRouter(prefix=prefix, tags=["runtime"])
        self._setup_routes()
        
    async def _create_module(self, request: CreateModuleRequest):
        """Create runtime module"""
        try:
            metadata = self.service.create_runtime_module(
                module_id=request.module_id,
                version=request.version,
                env_vars=request.env_vars
            )
            return RuntimeModuleResponse.from_metadata(metadata)
        except RuntimeModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _delete_module(self, runtime_id: str):
        """Delete runtime module"""
        try:
            self.service.delete_runtime_module(runtime_id)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Runtime module {runtime_id} deleted successfully"
                }
            )
        except RuntimeModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _create_relation(self, request: CreateRelationRequest):
        """Create module relation"""
        try:
            self.service.create_relation(
                source_id=request.source_id,
                target_id=request.target_id,
                relation_type=request.relation_type
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Relation created successfully"
                }
            )
        except RuntimeModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _delete_relation(self, source_id: str, target_id: str):
        """Delete module relation"""
        try:
            self.service.delete_relation(source_id, target_id)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Relation deleted successfully"
                }
            )
        except RuntimeModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _get_module_graph(self):
        """Get module relationship graph"""
        try:
            graph = self.service.get_module_graph()
            
            # Convert to response format
            nodes = []
            for node_id in graph.nodes:
                attrs = graph.nodes[node_id]
                nodes.append(
                    RuntimeModuleResponse(
                        id=node_id,
                        module_id=attrs['module_id'],
                        version=attrs['version'],
                        created_at=attrs['created_at'],
                        env_vars=attrs['env_vars'],
                        repo_name=attrs['repo_name']  # Changed from repo_path to repo_name
                    )
                )
                
            edges = []
            for source, target, attrs in graph.edges(data=True):
                edges.append({
                    "source": source,
                    "target": target,
                    "type": attrs['type'],
                    "created_at": attrs['created_at']
                })
                
            return ModuleGraphResponse(nodes=nodes, edges=edges)
            
        except RuntimeModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/module",
            self._create_module,
            methods=["POST"],
            response_model=RuntimeModuleResponse,
            summary="Create runtime module"
        )
        
        self.router.add_api_route(
            "/module/{runtime_id}",
            self._delete_module,
            methods=["DELETE"],
            summary="Delete runtime module"
        )
        
        self.router.add_api_route(
            "/relation",
            self._create_relation,
            methods=["POST"],
            summary="Create module relation"
        )
        
        self.router.add_api_route(
            "/relation/{source_id}/{target_id}",
            self._delete_relation,
            methods=["DELETE"],
            summary="Delete module relation" 
        )
        
        self.router.add_api_route(
            "/graph",
            self._get_module_graph,
            methods=["GET"],
            response_model=ModuleGraphResponse,
            summary="Get module graph"
        )