# tests/services/execution/test_model.py

import pytest
import os
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from pydantic import BaseModel
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from engine.services.execution.model import ModelService, MODEL_CONFIG_KEY, DEFAULT_MODEL
from engine.db.models import GlobalConfig


# --- Test Data ---
TEST_MODEL_NAME = "test-model-name"


# --- Pydantic Model for Testing ---
class TestResponse(BaseModel):
    result: str
    score: float


# --- Fixtures ---

@pytest.fixture
def mock_config(db_session: Session) -> GlobalConfig:
    """Create a model config in the database"""
    # Delete any existing configs
    db_session.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).delete()
    
    # Create new config
    config = GlobalConfig(
        key=MODEL_CONFIG_KEY,
        value=TEST_MODEL_NAME,
        description="Test model config"
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def model_service(db_session: Session):
    """Create a ModelService with patched database and initialization"""
    # Patch both instructor and the initialization to prevent actual model loading
    with patch('engine.services.execution.model.instructor.from_litellm'), \
         patch.object(ModelService, '_load_model_config'):
        
        # Create service with model loading mocked out
        service = ModelService()
        
        # Replace the _get_db method
        @contextmanager
        def test_db_context():
            try:
                yield db_session
            finally:
                pass
        
        service._get_db = test_db_context
        
        # Replace the _load_model_config to return our test value
        def load_from_test_db():
            try:
                config = db_session.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).one()
                return config.value
            except NoResultFound:
                return DEFAULT_MODEL
            
        service._load_model_config = load_from_test_db
        
        # Explicitly set the model name (needed for some tests)
        service.model_name = service._load_model_config()
        
        return service


# --- Test Cases ---

class TestModelService:

    def test_init_with_existing_config(self, db_session: Session, mock_config: GlobalConfig):
        """Test initialization with existing config loads from DB"""
        with patch('engine.services.execution.model.instructor.from_litellm'):
            # To test the real initialization, we need to mock just enough
            # to prevent actual API calls but allow the real DB loading
            
            # Create a fresh service instance
            service = ModelService()
            
            # Override DB session
            @contextmanager
            def test_db_context():
                try:
                    yield db_session
                finally:
                    pass
            
            # Replace _get_db and re-load config
            service._get_db = test_db_context
            service.model_name = service._load_model_config()
            
            # Should load existing config
            assert service.model_name == TEST_MODEL_NAME

    def test_init_with_no_config(self, db_session: Session):
        """Test initialization with no existing config creates default"""
        # Remove any existing configs
        db_session.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).delete()
        db_session.commit()
        
        with patch('engine.services.execution.model.instructor.from_litellm'):
            # Create service
            service = ModelService()
            
            # Override DB session
            @contextmanager
            def test_db_context():
                try:
                    yield db_session
                finally:
                    pass
            
            # Replace _get_db with our test version and re-load config
            service._get_db = test_db_context
            service.model_name = service._load_model_config()
            
            # Should create default config
            assert service.model_name == DEFAULT_MODEL
            
            # Verify in DB
            config = db_session.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).first()
            assert config is not None
            assert config.value == DEFAULT_MODEL

    def test_set_model(self, model_service: ModelService, db_session: Session):
        """Test setting model updates DB"""
        new_model = "new-test-model"
        
        result = model_service.set_model(new_model)
        
        # Should return new model name
        assert result == new_model
        assert model_service.model_name == new_model
        
        # Verify in DB
        config = db_session.query(GlobalConfig).filter(GlobalConfig.key == MODEL_CONFIG_KEY).first()
        assert config is not None
        assert config.value == new_model

    def test_get_current_model(self, model_service: ModelService, mock_config: GlobalConfig):
        """Test getting current model name"""
        # Force reload config
        model_service.model_name = model_service._load_model_config()
        
        assert model_service.get_current_model() == TEST_MODEL_NAME

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "ANTHROPIC_API_KEY": "test-key"})
    def test_get_available_models(self, model_service: ModelService):
        """Test getting available models based on env vars"""
        available_models = model_service.get_available_models()
        
        # Should include models for providers with API keys
        assert "openai" in available_models
        assert "anthropic" in available_models
        assert len(available_models["openai"]) > 0
        assert len(available_models["anthropic"]) > 0
        
        # Verify structure
        model = available_models["openai"][0]
        assert "name" in model
        assert "identifier" in model
        assert "label" in model

    @patch('engine.services.execution.model.instructor.from_litellm')
    def test_structured_output(self, mock_instructor, model_service: ModelService):
        """Test structured output calls instructor correctly"""
        # Setup mock
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        
        mock_response = (TestResponse(result="test", score=0.9), MagicMock())
        mock_client.chat.completions.create_with_completion.return_value = mock_response
        
        # Override the instructor client
        model_service.instructor_client = mock_client
        
        # Test params
        messages = [{"role": "user", "content": "Analyze this"}]
        
        # Call method
        result, raw = model_service.structured_output(
            messages=messages,
            response_model=TestResponse,
            temperature=0.2
        )
        
        # Verify correct params passed
        mock_client.chat.completions.create_with_completion.assert_called_once_with(
            model=model_service.model_name,
            messages=messages,
            response_model=TestResponse,
            temperature=0.2
        )
        
        assert isinstance(result, TestResponse)
        assert result.result == "test"
        assert result.score == 0.9


    @patch('engine.services.execution.model.instructor.from_litellm')
    def test_structured_output_error(self, mock_instructor, model_service: ModelService):
        """Test error handling in structured output"""
        # Setup mock
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        
        # Configure mock to raise exception
        mock_client.chat.completions.create_with_completion.side_effect = Exception("Parsing error")
        
        # Override the instructor client
        model_service.instructor_client = mock_client
        
        # Call method expecting exception
        with pytest.raises(Exception) as exc_info:
            model_service.structured_output(
                messages=[{"role": "user", "content": "Analyze this"}],
                response_model=TestResponse
            )
        
        # Verify exception message
        assert "Structured output generation failed: Parsing error" in str(exc_info.value)

    def test_load_model_config_error(self, model_service: ModelService):
        """Test error handling in loading model config"""
        # Mock _get_db to raise exception
        def raise_error():
            @contextmanager
            def context_manager():
                raise Exception("DB error")
                yield None
            return context_manager()
        
        model_service._get_db = raise_error
        
        # Should return default model on error
        assert model_service._load_model_config() == DEFAULT_MODEL