# engine/apis/action.py

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from engine.services.execution.action import ActionError, ActionService, FunctionMetadata


class OpenAIFunctionSchema(BaseModel):
    """OpenAI function calling schema"""
    type: str = "function"
    function: Dict[str, Any]

    @classmethod
    def from_metadata(cls, metadata: FunctionMetadata) -> "OpenAIFunctionSchema":
        """Convert function metadata to OpenAI schema"""
        return cls(
            type="function",
            function={
                "name": metadata.name,
                "description": metadata.description,
                "parameters": metadata.parameters,
                "strict": True
            }
        )

class ExecuteFunctionRequest(BaseModel):
    parameters: Dict[str, Any] = {}
    requirements: List[str] = []
    env_vars: Dict[str, str] = {}  # Add environment variables field

class ActionRouter:
    """FastAPI router for function execution"""

    def __init__(
        self,
        action_service: ActionService,
        prefix: str = "/action"
    ):
        self.service = action_service
        self.router = APIRouter(prefix=prefix, tags=["action"])
        self._setup_routes()

    async def _get_function_metadata(
        self,
        folder_path: str = Query(..., description="Path to folder containing Python files"),
        file_path: str = Query(..., description="Path to Python file (relative to folder_path)"),
        function_name: str = Query(..., description="Name of the function")
    ) -> OpenAIFunctionSchema:
        """Get function metadata in OpenAI schema format"""
        try:
            metadata = self.service.get_function_metadata(
                folder_path=folder_path,
                file_path=file_path,
                function_name=function_name
            )
            return OpenAIFunctionSchema.from_metadata(metadata)
        except ActionError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _execute_function(
        self,
        folder_path: str = Query(..., description="Path to folder containing Python files"),
        file_path: str = Query(..., description="Path to Python file (relative to folder_path)"),
        function_name: str = Query(..., description="Name of the function"),
        request: ExecuteFunctionRequest = None
    ) -> Dict[str, Any]:
        """Execute function"""
        try:
            if request is None:
                request = ExecuteFunctionRequest()

            result = self.service.execute_function(
                folder_path=folder_path,
                file_path=file_path,
                function_name=function_name,
                parameters=request.parameters,
                requirements=request.requirements,
                env_vars=request.env_vars  # Pass environment variables to service
            )
            return {"result": result}
        except ActionError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/metadata",
            self._get_function_metadata,
            methods=["GET"],
            response_model=OpenAIFunctionSchema,
            summary="Get function metadata in OpenAI schema format"
        )

        self.router.add_api_route(
            "/execute",
            self._execute_function,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Execute function with optional environment variables"
        )