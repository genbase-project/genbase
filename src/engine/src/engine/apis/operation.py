# engine/apis/operation.py

from fastapi import APIRouter, HTTPException, Query
from git import Union
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, get_origin, get_args
import inspect

from engine.services.operation import OperationService, OperationError, FunctionMetadata

def serialize_type(type_info: Any) -> str:
    """Convert Python type to string representation"""
    if type_info == Any:
        return "any"
    
    if get_origin(type_info):
        origin = get_origin(type_info)
        args = get_args(type_info)
        
        if origin in (list, List):
            return f"List[{serialize_type(args[0])}]"
        if origin in (dict, Dict):
            return f"Dict[{serialize_type(args[0])}, {serialize_type(args[1])}]"
        if origin == Union:
            return f"Union[{', '.join(serialize_type(arg) for arg in args)}]"
        return str(origin)
        
    if inspect.isclass(type_info):
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
    
    @classmethod
    def from_metadata(cls, metadata: FunctionMetadata) -> "FunctionMetadataResponse":
        # Convert parameter types to strings
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
            is_async=metadata.is_async
        )

class ExecuteFunctionRequest(BaseModel):
    parameters: Dict[str, Any] = {}
    sandbox: bool = True

class OperationRouter:
    """FastAPI router for function execution"""
    
    def __init__(
        self,
        operation_service: OperationService,
        prefix: str = "/operation"
    ):
        """
        Initialize operation router
        
        Args:
            operation_service: Operation service
            prefix: URL prefix for routes
        """
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
                request.parameters,
                sandbox=request.sandbox
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