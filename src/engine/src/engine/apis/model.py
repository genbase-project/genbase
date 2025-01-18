from typing import Any, Dict
from fastapi import APIRouter
from engine.services.model import ModelService


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
