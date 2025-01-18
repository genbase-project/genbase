# engine/apis/operation.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from engine.services.operation import OperationService, OperationError, FunctionMetadata

def serialize_type(type_info: Any) -> str:
    """Convert Python type to string representation"""
    if hasattr(type_info, "__name__"):
        return type_info.__name__
    return str(type_info)

class ParameterInfo(BaseModel):
    type: str
    default: Optional[Any] = None
    kind: str

class FunctionMetadataResponse(BaseModel):
    docstring: str
    parameters: Dict[str, ParameterInfo]
    return_type: str
    is_async: bool
    required_packages: List[str]
    
    @classmethod
    def from_metadata(cls, metadata: FunctionMetadata) -> "FunctionMetadataResponse":
        serialized_params = {}
        for name, param_info in metadata.parameters.items():
            serialized_params[name] = ParameterInfo(
                type=serialize_type(param_info['type']),
                default=param_info['default'],
                kind=param_info['kind']
            )
        
        return cls(
            docstring=metadata.docstring,
            parameters=serialized_params,
            return_type=serialize_type(metadata.return_type),
            is_async=metadata.is_async,
            required_packages=metadata.required_packages
        )

class ExecuteFunctionRequest(BaseModel):
    parameters: Dict[str, Any] = {}

class OperationRouter:
    """FastAPI router for function execution"""
    
    def __init__(
        self,
        operation_service: OperationService,
        prefix: str = "/operation"
    ):
        self.service = operation_service
        self.router = APIRouter(prefix=prefix, tags=["operation"])
        self._setup_routes()
    
    async def _get_function_metadata(
        self,
        file_path: str = Query(..., description="Path to the Python file"),
        function_name: str = Query(..., description="Name of the function")
    ):
        """Get function metadata"""
        try:
            metadata = self.service.get_function_metadata(file_path, function_name)
            return FunctionMetadataResponse.from_metadata(metadata)
        except OperationError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def _execute_function(
        self,
        file_path: str = Query(..., description="Path to the Python file"),
        function_name: str = Query(..., description="Name of the function"),
        request: ExecuteFunctionRequest = None
    ):
        """Execute function"""
        try:
            if request is None:
                request = ExecuteFunctionRequest()

            result = self.service.execute_function(
                file_path,
                function_name,
                request.parameters
            )
            return {"result": result}
        except OperationError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/metadata",
            self._get_function_metadata,
            methods=["GET"],
            response_model=FunctionMetadataResponse,
            summary="Get function metadata"
        )
        
        self.router.add_api_route(
            "/execute",
            self._execute_function,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Execute function"
        )