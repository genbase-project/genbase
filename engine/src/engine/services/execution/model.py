from typing import Any, Dict, List, Optional, Union, TypeVar, Type, Tuple
import os
from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from litellm import completion, ModelResponse
import instructor
import litellm

from loguru import logger
from engine.db.session import SessionLocal
from engine.db.models import GlobalConfig

litellm.suppress_debug_info = True

# Model mappings by provider and their required env vars
MODEL_CONFIGS = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "models": [
            {"name": "o1-mini", "identifier": "o1-mini", "label": "OpenAI o1-mini"},
            {"name": "o1-preview", "identifier": "o1-preview", "label": "OpenAI o1-preview"},
            {"name": "gpt-4o-mini", "identifier": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"name": "gpt-4o-mini-2024-07-18", "identifier": "gpt-4o-mini-2024-07-18", "label": "GPT-4o Mini (Jul 2024)"},
            {"name": "gpt-4o", "identifier": "gpt-4o", "label": "GPT-4o"},
            {"name": "gpt-4o-2024-08-06", "identifier": "gpt-4o-2024-08-06", "label": "GPT-4o (Aug 2024)"},
            {"name": "gpt-4o-2024-05-13", "identifier": "gpt-4o-2024-05-13", "label": "GPT-4o (May 2024)"},
            {"name": "gpt-4-turbo", "identifier": "gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"name": "gpt-4-0125-preview", "identifier": "gpt-4-0125-preview", "label": "GPT-4 (Jan 2024)"},
            {"name": "gpt-4-1106-preview", "identifier": "gpt-4-1106-preview", "label": "GPT-4 (Nov 2023)"},
            {"name": "gpt-3.5-turbo-1106", "identifier": "gpt-3.5-turbo-1106", "label": "GPT-3.5 Turbo (Nov 2023)"},
            {"name": "gpt-3.5-turbo", "identifier": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
            {"name": "gpt-3.5-turbo-0301", "identifier": "gpt-3.5-turbo-0301", "label": "GPT-3.5 Turbo (Mar 2023)"},
            {"name": "gpt-3.5-turbo-0613", "identifier": "gpt-3.5-turbo-0613", "label": "GPT-3.5 Turbo (Jun 2023)"},
            {"name": "gpt-3.5-turbo-16k", "identifier": "gpt-3.5-turbo-16k", "label": "GPT-3.5 Turbo 16k"},
            {"name": "gpt-3.5-turbo-16k-0613", "identifier": "gpt-3.5-turbo-16k-0613", "label": "GPT-3.5 Turbo 16k (Jun 2023)"},
            {"name": "gpt-4", "identifier": "gpt-4", "label": "GPT-4"},
            {"name": "gpt-4-0314", "identifier": "gpt-4-0314", "label": "GPT-4 (Mar 2023)"},
            {"name": "gpt-4-0613", "identifier": "gpt-4-0613", "label": "GPT-4 (Jun 2023)"},
            {"name": "gpt-4-32k", "identifier": "gpt-4-32k", "label": "GPT-4 32k"},
            {"name": "gpt-4-32k-0314", "identifier": "gpt-4-32k-0314", "label": "GPT-4 32k (Mar 2023)"},
            {"name": "gpt-4-32k-0613", "identifier": "gpt-4-32k-0613", "label": "GPT-4 32k (Jun 2023)"}
        ]
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "models": [
            {"name": "claude-3-5-sonnet-20241022", "identifier": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet (Oct 2024)"},
            {"name": "claude-3-5-sonnet-20240620", "identifier": "claude-3-5-sonnet-20240620", "label": "Claude 3.5 Sonnet (Jun 2024)"},
            {"name": "claude-3-haiku-20240307", "identifier": "claude-3-haiku-20240307", "label": "Claude 3 Haiku (Mar 2024)"},
            {"name": "claude-3-opus-20240229", "identifier": "claude-3-opus-20240229", "label": "Claude 3 Opus (Feb 2024)"}
        ]
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "models": [
            {"name": "mistral/mistral-small-latest", "identifier": "mistral-small-latest", "label": "Mistral Small (Latest)"},
            {"name": "mistral/mistral-medium-latest", "identifier": "mistral-medium-latest", "label": "Mistral Medium (Latest)"},
            {"name": "mistral/mistral-large-2407", "identifier": "mistral-large-2407", "label": "Mistral Large (Jul 2024)"},
            {"name": "mistral/mistral-large-latest", "identifier": "mistral-large-latest", "label": "Mistral Large (Latest)"},
            {"name": "mistral/open-mistral-7b", "identifier": "open-mistral-7b", "label": "Open Mistral 7B"},
            {"name": "mistral/open-mixtral-8x7b", "identifier": "open-mixtral-8x7b", "label": "Open Mixtral 8x7B"},
            {"name": "mistral/open-mixtral-8x22b", "identifier": "open-mixtral-8x22b", "label": "Open Mixtral 8x22B"},
            {"name": "mistral/codestral-latest", "identifier": "codestral-latest", "label": "Codestral (Latest)"},
            {"name": "mistral/open-mistral-nemo", "identifier": "open-mistral-nemo", "label": "Open Mistral Nemo"},
            {"name": "mistral/open-mistral-nemo-2407", "identifier": "open-mistral-nemo-2407", "label": "Open Mistral Nemo (Jul 2024)"},
            {"name": "mistral/open-codestral-mamba", "identifier": "open-codestral-mamba", "label": "Open Codestral Mamba"},
            {"name": "mistral/codestral-mamba-latest", "identifier": "codestral-mamba-latest", "label": "Codestral Mamba (Latest)"}
        ]
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "models": [
            {"name": "deepseek/deepseek-chat", "identifier": "deepseek-chat", "label": "DeepSeek Chat"},
            {"name": "deepseek/deepseek-coder", "identifier": "deepseek-coder", "label": "DeepSeek Coder"},
            {"name": "deepseek/deepseek-reasoner", "identifier": "deepseek-reasoner", "label": "DeepSeek Reasoner"}
        ]
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "models": [
            {"name": "groq/llama-3.1-8b-instant", "identifier": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant"},
            {"name": "groq/llama-3.1-70b-versatile", "identifier": "llama-3.1-70b-versatile", "label": "Llama 3.1 70B Versatile"},
            {"name": "groq/llama3-8b-8192", "identifier": "llama3-8b-8192", "label": "Llama 3 8B"},
            {"name": "groq/llama3-70b-8192", "identifier": "llama3-70b-8192", "label": "Llama 3 70B"},
            {"name": "groq/llama2-70b-4096", "identifier": "llama2-70b-4096", "label": "Llama 2 70B"},
            {"name": "groq/mixtral-8x7b-32768", "identifier": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
            {"name": "groq/gemma-7b-it", "identifier": "gemma-7b-it", "label": "Gemma 7B-IT"}
        ]
    }
}

# Constants
DEFAULT_MODEL = "gpt-4o"
MODEL_CONFIG_KEY = "model_name"

ResponseType = TypeVar('ResponseType', bound=BaseModel)


class ModelService:
    """Simple service for managing LLM interactions with database persistence"""

    def _get_db(self) -> Session:
        """Get database session"""
        return SessionLocal()

    def get_available_models(self) -> Dict[str, List[Dict[str, str]]]:
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

    def __init__(self):
        """Initialize the model service with persisted configuration if available"""
        self.instructor_client = instructor.from_litellm(completion)
        self.model_name = self._load_model_config()

    def _load_model_config(self) -> str:
        """Load model configuration from database or use default"""
        try:
            with self._get_db() as db:
                config = db.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).one()
                return config.value
        except NoResultFound:
            # If no configuration exists, set the default
            default_model = DEFAULT_MODEL
            self.set_model(default_model)
            return default_model
        except Exception as e:
            logger.error(f"Error loading model configuration: {str(e)}")
            return DEFAULT_MODEL

    def set_model(self, model_name: str) -> str:
        """
        Set the model name and persist to database
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            The new model name
        """
        self.model_name = model_name
        
        # Save to database
        try:
            with self._get_db() as db:
                try:
                    config = db.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).one()
                    config.value = model_name
                except NoResultFound:
                    # Create new config if it doesn't exist
                    config = GlobalConfig(
                        key=MODEL_CONFIG_KEY,
                        value=model_name,
                        description="Default model for LLM interactions"
                    )
                    db.add(config)
                db.commit()
        except Exception as e:
            logger.error(f"Error saving model configuration: {str(e)}")
            
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
        model: Optional[str] = None,
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
                model=model or self.model_name,
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