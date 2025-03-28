from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Response, Depends, Header, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel, Field
import litellm

from engine.services.execution.model import ModelService
from engine.services.core.api_key import ApiKeyService

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to verify API key using Bearer token"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Extract the token from credentials
    api_key = credentials.credentials
    
    module_id = ApiKeyService().validate_api_key(api_key)
    if not module_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return module_id


class LLMGatewayRouter:
    """
    FastAPI router for OpenAI API compatible endpoints using LiteLLM as backend
    with API key authentication
    """

    def __init__(
        self,
        model_service: ModelService,
        api_key_service: ApiKeyService,
        prefix: str = ""
    ):
        self.service = model_service
        self.api_key_service = api_key_service
        self.router = APIRouter(prefix=prefix, tags=["llm_gateway"])
        self._setup_routes()
        self.api_key_dependency = lambda: verify_api_key()


    async def _handle_chat_completion(self, request: Request, module_id: str = Depends(verify_api_key)):
        """
        Handle chat completion requests in OpenAI API format
        """
        try:
            # Parse request data
            request_data = await request.json()
            
            # Use the specified model or fall back to the default from ModelService
            if "model" not in request_data:
                request_data["model"] = self.service.get_current_model()
            
            # Add module_id to request context (could be used for logging/auditing)
            request_data["user"] = request_data.get("user", "") + f"|module:{module_id}"
            
            # Check if streaming is requested
            stream = request_data.get("stream", False)
            
            # Use litellm directly to avoid parameter conflicts
            if stream:
                return StreamingResponse(
                    self._stream_chat_completion(request_data),
                    media_type="text/event-stream"
                )
            else:
                # Handle regular response
                response = litellm.completion(**request_data)
                return response
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")
    
    async def _stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Stream chat completion chunks in OpenAI API format
        """
        try:
            # Ensure stream is set to True
            request_data["stream"] = True
            
            # Get streaming response
            stream_response = litellm.completion(**request_data)
            
            # Process each chunk
            for chunk in stream_response:
                # Convert chunk to JSON string and yield in SSE format
                chunk_dict = chunk.dict() if hasattr(chunk, 'dict') else chunk
                yield f"data: {json.dumps(chunk_dict)}\n\n"
            
            # Send end of stream
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {"error": {"message": str(e), "type": "server_error"}}
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

    async def _handle_completion(self, request: Request, module_id: str = Depends(verify_api_key)):
        """
        Handle completions requests in OpenAI API format
        """
        try:
            # Parse request data
            request_data = await request.json()
            
            # Extract parameters
            prompt = request_data.get("prompt", "")
            model = request_data.get("model")
            if not model:
                model = self.service.get_current_model()
            
            # Convert to chat format
            chat_request = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "user": request_data.get("user", "") + f"|module:{module_id}"
            }
            
            # Copy other parameters
            for key in ["temperature", "max_tokens", "top_p", "n", "stop", 
                        "presence_penalty", "frequency_penalty", "logit_bias"]:
                if key in request_data:
                    chat_request[key] = request_data[key]
            
            # Handle streaming
            stream = request_data.get("stream", False)
            chat_request["stream"] = stream
            
            if stream:
                return StreamingResponse(
                    self._stream_chat_completion(chat_request),
                    media_type="text/event-stream"
                )
            else:
                # Handle regular response
                response = litellm.completion(**chat_request)
                return response
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

    async def _list_models(self, module_id: str = Depends(verify_api_key)):
        """
        List available models in OpenAI API format
        """
        try:
            # Get available models from model service
            available_models = self.service.get_available_models()
            
            # Convert to OpenAI format
            models_list = []
            for provider, models in available_models.items():
                for model_info in models:
                    models_list.append({
                        "id": model_info["name"],
                        "object": "model",
                        "created": 1677610602,  # Placeholder timestamp
                        "owned_by": provider
                    })
            
            return {"data": models_list, "object": "list"}
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

    def _setup_routes(self):
        """Set up API routes"""
        # OpenAI API compatible endpoints
        self.router.add_api_route(
            "/chat/completions",
            self._handle_chat_completion,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/completions",
            self._handle_completion,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/models",
            self._list_models,
            methods=["GET"]
        )