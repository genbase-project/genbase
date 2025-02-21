from typing import Any, Dict, List, Optional, Union
import os
from litellm import embedding
from loguru import logger

# Suppress debug info
import litellm
litellm.suppress_debug_info = True

# Model configurations by provider and their required env vars
EMBEDDING_CONFIGS = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "models": [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002"
        ]
    },
    "cohere": {
        "env_var": "COHERE_API_KEY",
        "models": [
            "embed-english-v3.0",
            "embed-english-light-v3.0",
            "embed-multilingual-v3.0",
            "embed-multilingual-light-v3.0",
            "embed-english-v2.0",
            "embed-english-light-v2.0",
            "embed-multilingual-v2.0"
        ]
    },
    "azure": {
        "env_var": ["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION"],
        "models": ["text-embedding-ada-002"]  # Deployment names are custom
    },
    "vertex_ai": {
        "env_var": None,  # Requires project setup
        "models": [
            "textembedding-gecko",
            "textembedding-gecko-multilingual",
            "textembedding-gecko-multilingual@001",
            "textembedding-gecko@001",
            "textembedding-gecko@003",
            "text-embedding-preview-0409",
            "text-multilingual-embedding-preview-0409"
        ]
    },
    "bedrock": {
        "env_var": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME"],
        "models": [
            "amazon.titan-embed-text-v1",
            "cohere.embed-english-v3",
            "cohere.embed-multilingual-v3"
        ]
    },
    "nvidia_nim": {
        "env_var": ["NVIDIA_NIM_API_KEY", "NVIDIA_NIM_API_BASE"],
        "models": [
            "NV-Embed-QA",
            "nvidia/nv-embed-v1",
            "nvidia/nv-embedqa-mistral-7b-v2",
            "nvidia/nv-embedqa-e5-v5",
            "nvidia/embed-qa-4",
            "nvidia/llama-3.2-nv-embedqa-1b-v1",
            "nvidia/llama-3.2-nv-embedqa-1b-v2",
            "snowflake/arctic-embed-l",
            "baai/bge-m3"
        ]
    },
    "huggingface": {
        "env_var": "HUGGINGFACE_API_KEY",
        "models": [
            "microsoft/codebert-base",
            "BAAI/bge-large-zh"
            # Note: Supports all Feature-Extraction + Sentence Similarity models
        ]
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "models": ["mistral-embed"]
    },
    "gemini": {
        "env_var": "GEMINI_API_KEY",
        "models": ["text-embedding-004"]
    },
    "voyage": {
        "env_var": "VOYAGE_API_KEY",
        "models": [
            "voyage-01",
            "voyage-lite-01",
            "voyage-lite-01-instruct"
        ]
    }
}

class EmbeddingService:
    """Service for managing embedding model interactions using LiteLLM"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002"):
        """
        Initialize the embedding service
        
        Args:
            model_name: Name of the embedding model to use
        """
        self.model_name = model_name
        
    def get_available_models(self) -> Dict[str, List[str]]:
        """
        Get list of available embedding models based on environment variables
        
        Returns:
            Dictionary of provider: list of available models
        """
        available_models = {}
        
        for provider, config in EMBEDDING_CONFIGS.items():
            if provider == "vertex_ai":
                # Check for vertex project setup
                if hasattr(litellm, "vertex_project"):
                    available_models[provider] = config["models"]
                continue
                
            if isinstance(config["env_var"], list):
                # Check if all required env vars are present
                if all(os.environ.get(env_var) for env_var in config["env_var"]):
                    available_models[provider] = config["models"]
            elif os.environ.get(config["env_var"]):
                available_models[provider] = config["models"]
                
        return available_models
    
    def set_model(self, model_name: str) -> str:
        """
        Set the embedding model name
        
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
    
    async def get_embedding(
        self,
        input: Union[str, List[str]],
        dimensions: Optional[int] = None,   
        user: Optional[str] = None,
        encoding_format: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get embeddings for the input text
        
        Args:
            input: Text to embed, can be a string or list of strings
            dimensions: Optional number of dimensions for the embedding
            user: Optional unique identifier for the end-user
            encoding_format: Optional format for the embeddings ("float" or "base64")
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dictionary containing the embedding response
        """
        try:
            # Handle single string input
            if isinstance(input, str):
                input = [input]
                
            response = embedding(
                model=self.model_name,
                input=input,
                dimensions=dimensions,
                user=user,
                encoding_format=encoding_format,
                **kwargs
            )
            return response
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise Exception(f"Failed to generate embeddings: {str(e)}")
            
    def verify_api_key(self, provider: str) -> bool:
        """
        Verify if the necessary API keys/credentials are set for a provider
        
        Args:
            provider: Name of the provider to check
            
        Returns:
            Boolean indicating if the credentials are properly set
        """
        if provider not in EMBEDDING_CONFIGS:
            return False
            
        config = EMBEDDING_CONFIGS[provider]
        
        if provider == "vertex_ai":
            return hasattr(litellm, "vertex_project")
            
        if isinstance(config["env_var"], list):
            return all(os.environ.get(env_var) for env_var in config["env_var"])
            
        return bool(os.environ.get(config["env_var"]))

# Example usage:
"""
embedding_service = EmbeddingService()

# Check available models
available_models = embedding_service.get_available_models()
print("Available models:", available_models)

# Set a specific model
embedding_service.set_model("text-embedding-3-small")

# Get embeddings
async def get_embeddings():
    response = await embedding_service.get_embedding(
        input=["Hello world", "Another text"],
        dimensions=1024,  # Optional for some models
        user="user123"    # Optional
    )
    print(response)
"""