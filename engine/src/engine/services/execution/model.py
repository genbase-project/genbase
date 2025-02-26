from typing import Any, Dict, List, Optional, Union, TypeVar, Type, Tuple
import os
from pydantic import BaseModel

from litellm import completion, ModelResponse
import instructor
import litellm

from loguru import logger


litellm.suppress_debug_info = True

# Model mappings by provider and their required env vars
MODEL_CONFIGS = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "models": [
            "o1-mini", "o1-preview", "gpt-4o-mini", "gpt-4o-mini-2024-07-18",
            "gpt-4o", "gpt-4o-2024-08-06", "gpt-4o-2024-05-13", "gpt-4-turbo",
            "gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo", "gpt-3.5-turbo-0301", "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "gpt-4",
            "gpt-4-0314", "gpt-4-0613", "gpt-4-32k", "gpt-4-32k-0314",
            "gpt-4-32k-0613"
        ]
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "models": [
            "claude-3-5-sonnet-20241022",   "claude-3-5-sonnet-20240620", "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ]
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "models": [
            "mistral/mistral-small-latest", "mistral/mistral-medium-latest",
            "mistral/mistral-large-2407", "mistral/mistral-large-latest",
            "mistral/open-mistral-7b", "mistral/open-mixtral-8x7b",
            "mistral/open-mixtral-8x22b", "mistral/codestral-latest",
            "mistral/open-mistral-nemo", "mistral/open-mistral-nemo-2407",
            "mistral/open-codestral-mamba", "mistral/codestral-mamba-latest"
        ]
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "models": [
            "deepseek/deepseek-chat", "deepseek/deepseek-coder",
            "deepseek/deepseek-reasoner"
        ]
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "models": [
            "groq/llama-3.1-8b-instant", "groq/llama-3.1-70b-versatile",
            "groq/llama3-8b-8192", "groq/llama3-70b-8192",
            "groq/llama2-70b-4096", "groq/mixtral-8x7b-32768",
            "groq/gemma-7b-it"
        ]
    }
}

ResponseType = TypeVar('ResponseType', bound=BaseModel)


class ModelService:
    def get_available_models(self) -> Dict[str, List[str]]:
        """
        Get list of available models based on environment variables
        
        Returns:
            Dictionary of provider: list of available models
        """
        available_models = {}
        
        for provider, config in MODEL_CONFIGS.items():
            if os.environ.get(config["env_var"]):
                available_models[provider] = config["models"]
                
        return available_models

    """Simple service for managing LLM interactions"""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.model_name = model_name
        self.instructor_client = instructor.from_litellm(completion)

    
    def set_model(self, model_name: str) -> str:
        """
        Set the model name
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            The new model name
        """
        self.model_name = model_name
        return self.model_name

    def get_current_model(self) -> str:
        """
        Get the currently selected model name
        
        Returns:
            The current model name
        """
        return self.model_name

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



    def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[ResponseType],
        **kwargs
    ) -> Tuple[ResponseType, ModelResponse]:
        """
        Get structured output and raw completion response
        
        Args:
            messages: List of chat messages
            response_model: Pydantic model class for response validation
            **kwargs: Additional arguments to pass to completion
            
        Returns:
            Tuple of (structured_response, raw_completion)
        """
        try:
            return self.instructor_client.chat.completions.create_with_completion(
                model=self.model_name,
                messages=messages,
                response_model=response_model,
                **kwargs
            )
        except Exception as e:
            raise Exception(f"Structured output generation failed: {str(e)}")

