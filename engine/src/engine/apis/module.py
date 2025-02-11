import re
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

from engine.services.core.module import (
    ModuleError,
    ModuleMetadata,
    ModuleService,
    RelationType,
)
from engine.utils.logging import logger


class CreateModuleRequest(BaseModel):
    project_id: str
    owner: str
    kit_id: str
    version: str
    env_vars: Dict[str, str]
    path: str
    module_name: Optional[str] = None  # New optional field

    @validator('path')
    def validate_path(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$', v):
            raise ValueError('Path must be alphanumeric segments separated by dots')
        return v

class UpdateModulePathRequest(BaseModel):
    path: str
    project_id: str

    @validator('path')
    def validate_path(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$', v):
            raise ValueError('Path must be alphanumeric segments separated by dots')
        return v


class UpdateRelationDescriptionRequest(BaseModel):
    description: str

    @validator('description')
    def validate_description(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()



class UpdateModuleEnvVarRequest(BaseModel):
    env_var_name: str
    env_var_value: str
    
    @validator('env_var_name')
    def validate_env_var_name(cls, v):
        if not v.strip():
            raise ValueError('Environment variable name cannot be empty')
        return v.strip()

class UpdateModuleNameRequest(BaseModel):
    name: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Module name cannot be empty')
        return v.strip()
    
class ModuleResponse(BaseModel):
    module_id: str
    module_name: Optional[str]  # New field
    project_id: str
    kit_id: str
    owner: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str
    path: str

    @classmethod
    def from_metadata(cls, metadata: ModuleMetadata) -> "ModuleResponse":
        return cls(
            module_id=metadata.module_id,
            module_name=metadata.module_name,  # New field
            project_id=metadata.project_id,
            kit_id=metadata.kit_id,
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
    description: Optional[str] = None  # New optional field


class ModuleGraphResponse(BaseModel):
    nodes: List[ModuleResponse]
    edges: List[Dict]

class ModuleRouter:
    """FastAPI router for module management"""

    def __init__(
        self,
        module_service: ModuleService,
        prefix: str = "/module"
    ):
        self.service = module_service
        self.router = APIRouter(prefix=prefix, tags=["module"])
        self._setup_routes()

    async def _create_module(self, request: CreateModuleRequest):
        """Create module"""
        try:
            metadata = self.service.create_module(
                project_id=request.project_id,
                owner=request.owner,
                kit_id=request.kit_id,
                version=request.version,
                env_vars=request.env_vars,
                path=request.path,
                module_name=request.module_name
            )
            return ModuleResponse.from_metadata(metadata)
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _delete_module(self, module_id: str):
        """Delete module"""
        try:
            self.service.delete_module(module_id)
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"module {module_id} deleted successfully"
                }
            )
        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _update_module_path(
        self,
        module_id: str,
        request: UpdateModulePathRequest
    ):
        """Update module path for a specific module in a project"""
        try:
            self.service.update_module_path(
                module_id=module_id,
                project_id=request.project_id,
                new_path=request.path
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Module path updated successfully"
                }
            )
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _create_relation(self, request: CreateRelationRequest):
        """Create module relation"""
        try:
            self.service.create_relation(
                source_id=request.source_id,
                target_id=request.target_id,
                relation_type=request.relation_type,
                description=request.description
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Relation created successfully"
                }
            )
        except ModuleError as e:
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
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_module_graph(self):
        """Get module relationship graph"""
        try:
            graph = self.service.get_module_graph()

            nodes = []
            for node_id in graph.nodes:
                attrs = graph.nodes[node_id]
                if 'kit_id' not in attrs:
                    continue

                logger.info(attrs)
                nodes.append(
                    ModuleResponse(
                        module_id=node_id,
                        kit_id=attrs['kit_id'],
                        module_name=attrs.get('module_name'),  # New field
                        owner=attrs['owner'],
                        version=attrs['version'],
                        created_at=attrs['created_at'].isoformat(),
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
                    "created_at": attrs['created_at'],
                    "description": attrs.get('description')
                })

            return ModuleGraphResponse(nodes=nodes, edges=edges)

        except ModuleError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_project_modules(self, project_id: str):
        """Get all modules for a project"""
        try:
            modules = self.service.get_project_modules(project_id)
            return [ModuleResponse.from_metadata(m) for m in modules]
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_linked_modules(
        self,
        module_id: str,
        relation_type: Optional[RelationType] = None
    ):
        """Get modules linked to the specified module"""
        try:
            modules = self.service.get_linked_modules(
                module_id=module_id,
                relation_type=relation_type
            )
            return [ModuleResponse.from_metadata(m) for m in modules]
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_module_connections(self, module_id: str):
        """Get modules with connection relation (bi-directional)"""
        return await self._get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.CONNECTION
        )

    async def get_module_context(self, module_id: str):
        """Get modules with context relation (bi-directional)"""
        return await self._get_linked_modules(
            module_id=module_id,
            relation_type=RelationType.CONTEXT
        )



    async def _update_module_env_var(
        self,
        module_id: str,
        request: UpdateModuleEnvVarRequest
    ):
        """Update module environment variable"""
        try:
            metadata = self.service.update_module_env_var(
                module_id=module_id,
                env_var_name=request.env_var_name,
                env_var_value=request.env_var_value
            )
            return ModuleResponse.from_metadata(metadata)
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _update_module_name(
        self,
        module_id: str,
        request: UpdateModuleNameRequest
    ):
        """Update module name"""
        try:
            metadata = self.service.update_module_name(
                module_id=module_id,
                new_name=request.name
            )
            return ModuleResponse.from_metadata(metadata)
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))




    async def _update_relation_description(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        request: UpdateRelationDescriptionRequest
    ):
        """Update relation description"""
        try:
            self.service.update_relation_description(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                new_description=request.description
            )
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Relation description updated successfully"
                }
            )
        except ModuleError as e:
            raise HTTPException(status_code=400, detail=str(e))


    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/",
            self._create_module,
            methods=["POST"],
            response_model=ModuleResponse,
            summary="Create module"
        )

        self.router.add_api_route(
            "/{module_id}",
            self._delete_module,
            methods=["DELETE"],
            summary="Delete module"
        )

        self.router.add_api_route(
            "/{module_id}/path",
            self._update_module_path,
            methods=["PUT"],
            summary="Update module path"
        )

        self.router.add_api_route(
            "/project/{project_id}/list",
            self._get_project_modules,
            methods=["GET"],
            response_model=List[ModuleResponse],
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
            "/{module_id}/connections",
            self.get_module_connections,
            methods=["GET"],
            response_model=List[ModuleResponse],
            summary="Get modules with connection relation to this module"
        )

        self.router.add_api_route(
            "/{module_id}/context",
            self.get_module_context,
            methods=["GET"],
            response_model=List[ModuleResponse],
            summary="Get modules with context relation to this module"
        )


        self.router.add_api_route(
            "/{module_id}/name",
            self._update_module_name,
            methods=["PUT"],
            response_model=ModuleResponse,
            summary="Update module name"
        )

        self.router.add_api_route(
            "/{module_id}/env",
            self._update_module_env_var,
            methods=["PUT"],
            response_model=ModuleResponse,
            summary="Update module environment variable"
        )


        self.router.add_api_route(
            "/relation/{source_id}/{target_id}/{relation_type}/description",
            self._update_relation_description,
            methods=["PUT"],
            summary="Update relation description"
        )
