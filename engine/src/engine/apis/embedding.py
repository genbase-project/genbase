from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engine.services.storage.embedder import EmbeddingService

class EmbeddingRequest(BaseModel):
    """Request model for embedding generation"""
    input: Union[str, List[str]]
    dimensions: Optional[int] = None
    user: Optional[str] = None
    encoding_format: Optional[str] = None
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)

class SetModelRequest(BaseModel):
    """Request model for setting the model name"""
    model_name: str

class VerifyAPIKeyRequest(BaseModel):
    """Request model for verifying provider API key"""
    provider: str

class EmbeddingRouter:
    """FastAPI router for embedding model endpoints"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        prefix: str = "/embedding"
    ):
        """
        Initialize the embedding router
        
        Args:
            embedding_service: Instance of EmbeddingService
            prefix: API route prefix
        """
        self.service = embedding_service
        self.router = APIRouter(prefix=prefix, tags=["embedding"])
        self._setup_routes()

    async def _get_embedding(self, request: EmbeddingRequest):
        """Handle embedding generation request"""
        try:
            response = await self.service.get_embedding(
                input=request.input,
                dimensions=request.dimensions,
                user=request.user,
                encoding_format=request.encoding_format,
                **request.model_kwargs
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _set_model(self, request: SetModelRequest):
        """Handle set model request"""
        try:
            model_name = self.service.set_model(request.model_name)
            return {"model_name": model_name}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_current_model(self):
        """Handle get current model request"""
        try:
            model_name = self.service.get_current_model()
            return {"model_name": model_name}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _list_models(self):
        """Handle list available models request"""
        try:
            available_models = self.service.get_available_models()
            return available_models
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _verify_api_key(self, request: VerifyAPIKeyRequest):
        """Handle API key verification request"""
        try:
            is_valid = self.service.verify_api_key(request.provider)
            return {"is_valid": is_valid}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _setup_routes(self):
        """Setup API routes"""
        self.router.add_api_route(
            "/generate",
            self._get_embedding,
            methods=["POST"],
            response_model=Dict[str, Any]
        )
        self.router.add_api_route(
            "/set",
            self._set_model,
            methods=["POST"],
            response_model=Dict[str, str]
        )
        self.router.add_api_route(
            "/list",
            self._list_models,
            methods=["GET"],
            response_model=Dict[str, List[str]]
        )
        self.router.add_api_route(
            "/current",
            self._get_current_model,
            methods=["GET"],
            response_model=Dict[str, str]
        )
        self.router.add_api_route(
            "/verify",
            self._verify_api_key,
            methods=["POST"],
            response_model=Dict[str, bool]
        )
