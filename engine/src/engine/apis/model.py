from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from engine.services.execution.model import ModelService

class SetModelRequest(BaseModel):
    """Request model for setting the model name"""
    model_name: str


class ModelRouter:
    """FastAPI router for model endpoints"""

    def __init__(
        self,
        model_service: ModelService,
        prefix: str = "/model"
    ):
        self.service = model_service
        self.router = APIRouter(prefix=prefix, tags=["model"])
        self._setup_routes()

    async def _set_model(self, request: SetModelRequest):
        """Handle set model request"""
        try:
            model_name = self.service.set_model(request.model_name)
            return {"model_name": model_name}
        except Exception as e:
            raise Exception(str(e))

    async def _get_current_model(self):
        """Handle get current model request"""
        try:
            model_name = self.service.get_current_model()
            return {"model_name": model_name}
        except Exception as e:
            raise Exception(str(e))

    async def _list_models(self):
        """Handle list models request"""
        try:
            available_models = self.service.get_available_models()
            return available_models
        except Exception as e:
            raise Exception(str(e))

    async def _chat_completion(self, request: Dict[str, Any]):
        """Handle chat completion request"""
        try:
            response = await self.service.chat_completion(**request)
            return response
        except Exception as e:
            raise Exception(str(e))

    def _setup_routes(self):
        """Setup API routes"""
        self.router.add_api_route(
            "/chat/completions",
            self._chat_completion,
            methods=["POST"]
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
