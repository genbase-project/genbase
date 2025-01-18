from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, APIRouter
from litellm import completion

class ModelService:
    """Simple service for managing LLM interactions"""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.model_name = model_name

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, str]]] = None,
        **kwargs
    ):
        """
        Get chat completion from model
        
        Args:
            messages: List of chat messages
            stream: Whether to stream the response
            tools: Optional list of tools/functions
            tool_choice: Optional tool choice configuration
            **kwargs: Additional arguments to pass to completion
        """
        try:
            response = completion(
                model=self.model_name,
                messages=messages,
                stream=stream,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )
            return response
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")
