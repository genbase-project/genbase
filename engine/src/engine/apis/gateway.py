from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Response, Depends, Header, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel, Field
import litellm
import uuid
from datetime import datetime, UTC

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
        Stream chat completion chunks in OpenAI API format using server-sent events
        """
        try:
            # Ensure stream is set to True
            request_data["stream"] = True
            
            # Generate IDs for the response and message
            response_id = f"resp_{uuid.uuid4().hex}"
            message_id = f"msg_{uuid.uuid4().hex}"
            timestamp = int(datetime.now(UTC).timestamp())
            model = request_data.get("model", self.service.get_current_model())
            
            # Send initial response.created event
            initial_response = {
                "type": "response.created",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created_at": timestamp,
                    "status": "in_progress",
                    "error": None,
                    "incomplete_details": None,
                    "instructions": request_data.get("instructions"),
                    "max_output_tokens": request_data.get("max_tokens"),
                    "model": model,
                    "output": [],
                    "parallel_tool_calls": True,
                    "previous_response_id": request_data.get("previous_response_id"),
                    "reasoning": {
                        "effort": None,
                        "generate_summary": None
                    },
                    "store": True,
                    "temperature": request_data.get("temperature", 1.0),
                    "text": {
                        "format": {
                            "type": "text"
                        }
                    },
                    "tool_choice": request_data.get("tool_choice", "auto"),
                    "tools": request_data.get("tools", []),
                    "top_p": request_data.get("top_p", 1.0),
                    "truncation": request_data.get("truncation", "disabled"),
                    "usage": None,
                    "user": request_data.get("user"),
                    "metadata": {}
                }
            }
            yield f"data: {json.dumps(initial_response)}\n\n"
            
            # Send in_progress event
            in_progress = {
                "type": "response.in_progress",
                "response": initial_response["response"]
            }
            yield f"data: {json.dumps(in_progress)}\n\n"
            
            # Add message container to output
            message_event = {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {
                    "id": message_id,
                    "status": "in_progress",
                    "type": "message",
                    "role": "assistant",
                    "content": []
                }
            }
            yield f"data: {json.dumps(message_event)}\n\n"
            
            # Add content part for text
            content_event = {
                "type": "response.content_part.added",
                "item_id": message_id,
                "output_index": 0,
                "content_index": 0,
                "part": {
                    "type": "output_text",
                    "text": "",
                    "annotations": []
                }
            }
            yield f"data: {json.dumps(content_event)}\n\n"
            
            # Get streaming response from LiteLLM
            full_text = ""
            stream_response = litellm.completion(**request_data)
            
            # Process each chunk
            for chunk in stream_response:
                # Allow other tasks to run between chunks
                await asyncio.sleep(0)
                
                # Extract text from chunk
                chunk_dict = chunk.dict() if hasattr(chunk, 'dict') else chunk
                delta_text = ""
                
                if "choices" in chunk_dict and chunk_dict["choices"]:
                    choice = chunk_dict["choices"][0]
                    if "delta" in choice and "content" in choice["delta"]:
                        delta_text = choice["delta"]["content"]
                
                # If we have text, send a delta event
                if delta_text:
                    full_text += delta_text
                    delta_event = {
                        "type": "response.output_text.delta",
                        "item_id": message_id,
                        "output_index": 0,
                        "content_index": 0,
                        "delta": delta_text
                    }
                    yield f"data: {json.dumps(delta_event)}\n\n"
            
            # Mark content part as done
            content_done_event = {
                "type": "response.content_part.done",
                "item_id": message_id,
                "output_index": 0,
                "content_index": 0,
                "part": {
                    "type": "output_text",
                    "text": full_text,
                    "annotations": []
                }
            }
            yield f"data: {json.dumps(content_done_event)}\n\n"
            
            # Mark message as done
            message_done_event = {
                "type": "response.output_item.done",
                "output_index": 0,
                "item": {
                    "id": message_id,
                    "status": "completed",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": full_text,
                            "annotations": []
                        }
                    ]
                }
            }
            yield f"data: {json.dumps(message_done_event)}\n\n"
            
            # Estimate token usage (this is approximate)
            input_tokens = len(" ".join([msg["content"] for msg in request_data.get("messages", [])])) // 4
            output_tokens = len(full_text) // 4
            
            # Mark response as completed
            completion_event = {
                "type": "response.completed",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created_at": timestamp,
                    "status": "completed",
                    "error": None,
                    "incomplete_details": None,
                    "instructions": request_data.get("instructions"),
                    "max_output_tokens": request_data.get("max_tokens"),
                    "model": model,
                    "output": [
                        {
                            "id": message_id,
                            "type": "message",
                            "status": "completed", 
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": full_text,
                                    "annotations": []
                                }
                            ]
                        }
                    ],
                    "parallel_tool_calls": True,
                    "previous_response_id": request_data.get("previous_response_id"),
                    "reasoning": {
                        "effort": None,
                        "generate_summary": None
                    },
                    "store": True,
                    "temperature": request_data.get("temperature", 1.0),
                    "text": {
                        "format": {
                            "type": "text"
                        }
                    },
                    "tool_choice": request_data.get("tool_choice", "auto"),
                    "tools": request_data.get("tools", []),
                    "top_p": request_data.get("top_p", 1.0),
                    "truncation": request_data.get("truncation", "disabled"),
                    "usage": {
                        "input_tokens": input_tokens,
                        "input_tokens_details": {
                            "cached_tokens": 0
                        },
                        "output_tokens": output_tokens,
                        "output_tokens_details": {
                            "reasoning_tokens": 0
                        },
                        "total_tokens": input_tokens + output_tokens
                    },
                    "user": request_data.get("user"),
                    "metadata": {}
                }
            }
            yield f"data: {json.dumps(completion_event)}\n\n"
            
            # Send end of stream in original format for backward compatibility
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Create error response
            error_data = {
                "type": "response.failed",
                "response": {
                    "id": f"resp_{uuid.uuid4().hex}",
                    "object": "response",
                    "created_at": int(datetime.now(UTC).timestamp()),
                    "status": "failed",
                    "error": {
                        "code": "server_error",
                        "message": str(e)
                    },
                    "model": request_data.get("model", self.service.get_current_model()),
                    "output": []
                }
            }
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