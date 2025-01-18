from fastapi import APIRouter, HTTPException
from engine.utils.logging import logger
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
from pydantic import BaseModel, validator
import re
from enum import Enum

from engine.services.runtime_module import (
    RuntimeModuleService,
    RuntimeModuleError,
    RuntimeModuleMetadata,
    RelationType
)

class CreateModuleRequest(BaseModel):
    project_id: str
    owner: str
    module_id: str
    version: str
    env_vars: Dict[str, str]
    path: str

    @validator('path')
    def validate_path(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$', v):
            raise ValueError('Path must be alphanumeric segments separated by dots')
        return v

class UpdateModulePathRequest(BaseModel):
    path: str
    project_id: str  # Added to specify which project's path to update

    @validator('path')
    def validate_path(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$', v):
            raise ValueError('Path must be alphanumeric segments separated by dots')
        return v

class RuntimeModuleResponse(BaseModel):
    id: str
    project_id: str
    module_id: str
    owner: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str
    path: str

    @classmethod
    def from_metadata(cls, metadata: RuntimeModuleMetadata) -> "RuntimeModuleResponse":
        return cls(
            id=metadata.id,
            project_id=metadata.project_id,
            module_id=metadata.module_id,
            owner=metadata.owner,
            version=metadata.version,
            created_at=metadata.created_at,
            env_vars=metadata.env_vars,
            repo_name=metadata.repo_name,
            path=metadata.path
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
                project_id=request.project_id,
                owner=request.owner,
                module_id=request.module_id,
                version=request.version,
                env_vars=request.env_vars,
                path=request.path
            )
            return RuntimeModuleResponse.from_metadata(metadata)
        except RuntimeModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
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

    async def _update_module_path(
        self,
        runtime_id: str,  # Now using runtime_id instead of project_id/module_id
        request: UpdateModulePathRequest
    ):
        """Update module path for a specific runtime module in a project"""
        try:
            self.service.update_module_path(
                runtime_id=runtime_id,
                project_id=request.project_id,
                new_path=request.path
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Module path updated successfully"
                }
            )
        except RuntimeModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
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
            raise HTTPException(status_code=400, detail=str(e))
    
    async def _delete_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType
    ):
        """Delete module relation"""
        try:
            self.service.delete_relation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Relation deleted successfully"
                }
            )
        except RuntimeModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_module_graph(self):
        """Get module relationship graph"""
        try:
            graph = self.service.get_module_graph()
            
            # Convert to response format
            nodes = []
            for node_id in graph.nodes:

                attrs = graph.nodes[node_id]

                # check empty nodes
                if 'module_id' not in attrs:
                    continue

                logger.info(attrs)
              

                nodes.append(
                    RuntimeModuleResponse(
                        id=node_id,
                        module_id=attrs['module_id'],
                        owner=attrs['owner'],
                        version=attrs['version'],
                        created_at=attrs['created_at'],
                        env_vars=attrs['env_vars'],
                        repo_name=attrs['repo_name'],
                        project_id=attrs['project_id'],
                        path=attrs['path']
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

    async def _get_project_modules(self, project_id: str):
        """Get all runtime modules for a project"""
        try:
            modules = self.service.get_project_modules(project_id)
            return [RuntimeModuleResponse.from_metadata(m) for m in modules]
        except RuntimeModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))
        



    async def _get_linked_modules(
        self,
        module_id: str,
        relation_type: Optional[RelationType] = None,
        as_dependent: bool = False
    ):
        """Get modules linked to the specified module"""
        try:
            modules = self.service.get_linked_modules(
                module_id=module_id,
                relation_type=relation_type,
                as_dependent=as_dependent
            )
            return [RuntimeModuleResponse.from_metadata(m) for m in modules]
        except RuntimeModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_module_dependents(self, module_id: str):
        """Get modules that depend on this module"""
        return await self._get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.DEPENDENCY,
            as_dependent=True
        )

    async def get_module_dependencies(self, module_id: str):
        """Get modules this module depends on"""
        return await self._get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.DEPENDENCY,
            as_dependent=False
        )

    async def get_module_context(self, module_id: str):
        """Get modules with context relation (bi-directional)"""
        return await self._get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.CONTEXT,
            as_dependent=False  # This will be ignored for context relations
        )

















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
            "/module/{runtime_id}/path",
            self._update_module_path,
            methods=["PUT"],
            summary="Update module path"
        )
        
        self.router.add_api_route(
            "/project/{project_id}/modules",
            self._get_project_modules,
            methods=["GET"],
            response_model=List[RuntimeModuleResponse],
            summary="Get all modules in a project"
        )
        
        self.router.add_api_route(
            "/relation",
            self._create_relation,
            methods=["POST"],
            summary="Create module relation"
        )
        
        self.router.add_api_route(
            "/relation/{source_id}/{target_id}/{relation_type}",
            self._delete_relation,
            methods=["DELETE"],
            summary="Delete module relation"
        )
        
        self.router.add_api_route(
            "/graph",
            self.get_module_graph,
            methods=["GET"],
            response_model=ModuleGraphResponse,
            summary="Get module graph"
        )


        self.router.add_api_route(
            "/module/{module_id}/dependents",
            self.get_module_dependents,
            methods=["GET"],
            response_model=List[RuntimeModuleResponse],
            summary="Get modules that depend on this module"
        )
        
        # Get modules this module depends on
        self.router.add_api_route(
            "/module/{module_id}/dependencies",
            self.get_module_dependencies,
            methods=["GET"],
            response_model=List[RuntimeModuleResponse],
            summary="Get modules this module depends on"
        )
        
        # Get modules with context relation
        self.router.add_api_route(
            "/module/{module_id}/context",
            self.get_module_context,
            methods=["GET"],
            response_model=List[RuntimeModuleResponse],
            summary="Get modules with context relation to this module"
        )
