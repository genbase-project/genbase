# tests/services/agents/test_chat_history.py

import pytest
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC, timedelta
from contextlib import contextmanager

from sqlalchemy.orm import Session
from litellm import ChatCompletionMessageToolCall

from engine.services.agents.chat_history import ChatHistoryManager, AgentError
from engine.db.models import ChatHistory

# --- Constants ---
TEST_MODULE_ID = "test-module-123"
TEST_PROFILE = "test-profile"
DEFAULT_SESSION_ID = str(uuid.UUID(int=0))
TEST_SESSION_ID = "test-session-789"
TEST_TOOL_CALL_ID = "test-tool-call-123"

# --- Fixtures ---

@pytest.fixture
def chat_history_manager(db_session: Session) -> ChatHistoryManager:
    """Create a ChatHistoryManager with test database session"""
    manager = ChatHistoryManager()
    
    # Override the database session with a context manager
    def get_test_db():
        @contextmanager
        def test_db_context():
            try:
                yield db_session
            finally:
                pass
        return test_db_context()
    
    manager._db = get_test_db()
    
    return manager

@pytest.fixture
def sample_chat_history(db_session: Session) -> list:
    """Create sample chat history in the database"""
    # Create a few messages
    messages = [
        ChatHistory(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="user",
            content="Hello, how can you help me?",
            timestamp=datetime.now(UTC) - timedelta(minutes=5),
            message_type="text",
            session_id=DEFAULT_SESSION_ID
        ),
        ChatHistory(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="assistant",
            content="I can help you with various tasks. What do you need?",
            timestamp=datetime.now(UTC) - timedelta(minutes=4),
            message_type="text",
            session_id=DEFAULT_SESSION_ID
        ),
        ChatHistory(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="user",
            content="Tell me the weather",
            timestamp=datetime.now(UTC) - timedelta(minutes=3),
            message_type="text",
            session_id=DEFAULT_SESSION_ID
        ),
    ]
    
    # Add a tool call message
    tool_call = ChatCompletionMessageToolCall(
        id=TEST_TOOL_CALL_ID,
        type="function",
        function={"name": "get_weather", "arguments": '{"location": "New York"}'}
    )
    
    messages.append(
        ChatHistory(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="assistant",
            content=None,
            timestamp=datetime.now(UTC) - timedelta(minutes=2),
            message_type="tool_call",
            tool_calls=[tool_call.model_dump_json()],
            session_id=DEFAULT_SESSION_ID
        )
    )
    
    # Add a tool result message
    messages.append(
        ChatHistory(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="tool",
            content='{"temperature": 72, "condition": "sunny"}',
            timestamp=datetime.now(UTC) - timedelta(minutes=1),
            message_type="tool_result",
            tool_call_id=TEST_TOOL_CALL_ID,
            name="get_weather",
            session_id=DEFAULT_SESSION_ID
        )
    )
    
    # Add everything to the database
    for msg in messages:
        db_session.add(msg)
    
    db_session.commit()
    
    # Create a different session with one message
    different_session_msg = ChatHistory(
        module_id=TEST_MODULE_ID,
        profile=TEST_PROFILE,
        role="user",
        content="This is from a different session",
        timestamp=datetime.now(UTC),
        message_type="text",
        session_id=TEST_SESSION_ID
    )
    
    db_session.add(different_session_msg)
    db_session.commit()
    
    return messages

# --- Test Cases ---

class TestChatHistoryManager:

    def test_get_chat_history_default_session(self, chat_history_manager: ChatHistoryManager, sample_chat_history: list):
        """Test getting chat history for default session"""
        # Get history without specifying session ID (should use default)
        history = chat_history_manager.get_chat_history(TEST_MODULE_ID, TEST_PROFILE)
        
        # Should have 5 messages from default session
        assert len(history) == 5
        
        # Verify order (ascending by timestamp)
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello, how can you help me?"
        
        # Verify tool call formatting
        assert "tool_calls" in history[3]
        assert history[3]["tool_calls"][0].id == TEST_TOOL_CALL_ID
        assert history[3]["tool_calls"][0].function.name == "get_weather"
        
        # Verify tool result formatting
        assert history[4]["role"] == "tool"
        assert history[4]["tool_call_id"] == TEST_TOOL_CALL_ID
        assert history[4]["name"] == "get_weather"

    def test_get_chat_history_specific_session(self, chat_history_manager: ChatHistoryManager, sample_chat_history: list):
        """Test getting chat history for specific session"""
        history = chat_history_manager.get_chat_history(TEST_MODULE_ID, TEST_PROFILE, session_id=TEST_SESSION_ID)
        
        # Should have 1 message from the specified session
        assert len(history) == 1
        assert history[0]["content"] == "This is from a different session"

    def test_get_chat_history_with_json_formatting(self, chat_history_manager: ChatHistoryManager, sample_chat_history: list):
        """Test getting chat history with JSON formatting for tool calls"""
        history = chat_history_manager.get_chat_history(TEST_MODULE_ID, TEST_PROFILE, return_json=True)
        
        # Verify tool call is returned as JSON dict instead of model instance
        assert "tool_calls" in history[3]
        assert isinstance(history[3]["tool_calls"][0], dict)
        assert history[3]["tool_calls"][0]["id"] == TEST_TOOL_CALL_ID
        assert history[3]["tool_calls"][0]["function"]["name"] == "get_weather"

    def test_add_to_history_text_message(self, chat_history_manager: ChatHistoryManager, db_session: Session):
        """Test adding a text message to history"""
        chat_history_manager.add_to_history(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="user",
            content="This is a new message"
        )
        
        # Query the database to verify
        messages = db_session.query(ChatHistory).filter_by(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            content="This is a new message"
        ).all()
        
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].session_id == DEFAULT_SESSION_ID
        assert messages[0].message_type == "text"
        assert messages[0].tool_calls is None

    def test_add_to_history_with_tool_calls(self, chat_history_manager: ChatHistoryManager, db_session: Session):
        """Test adding a message with tool calls to history"""
        tool_call = ChatCompletionMessageToolCall(
            id="new-tool-call-id",
            type="function",
            function={"name": "search_web", "arguments": '{"query": "python testing"}'}
        )
        
        chat_history_manager.add_to_history(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="assistant",
            content=None,
            message_type="tool_call",
            tool_calls=[tool_call],
            session_id=TEST_SESSION_ID
        )
        
        # Query the database to verify
        messages = db_session.query(ChatHistory).filter_by(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            message_type="tool_call",
            session_id=TEST_SESSION_ID
        ).all()
        
        assert len(messages) == 1
        assert messages[0].role == "assistant"
        assert messages[0].tool_calls is not None
        assert len(messages[0].tool_calls) == 1
        
        # Parse the tool call JSON to verify
        tool_call_data = ChatCompletionMessageToolCall.model_validate_json(messages[0].tool_calls[0])
        assert tool_call_data.id == "new-tool-call-id"
        assert tool_call_data.function.name == "search_web"

    def test_add_to_history_tool_result(self, chat_history_manager: ChatHistoryManager, db_session: Session):
        """Test adding a tool result to history"""
        chat_history_manager.add_to_history(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="tool",
            content='{"results": ["item1", "item2"]}',
            message_type="tool_result",
            tool_call_id="new-tool-call-id",
            name="search_web"
        )
        
        # Query the database to verify
        messages = db_session.query(ChatHistory).filter_by(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="tool",
            name="search_web"
        ).all()
        
        assert len(messages) == 1
        assert messages[0].tool_call_id == "new-tool-call-id"
        assert messages[0].content == '{"results": ["item1", "item2"]}'

    def test_get_last_message(self, chat_history_manager: ChatHistoryManager, sample_chat_history: list):
        """Test getting the last assistant message"""
        last_message = chat_history_manager.get_last_message(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE
        )
        
        # Last assistant message should be the tool call
        assert last_message is not None
        assert last_message["role"] == "assistant"
        assert "tool_calls" in last_message
        assert last_message["tool_calls"][0].id == TEST_TOOL_CALL_ID

    def test_get_last_message_by_role(self, chat_history_manager: ChatHistoryManager, sample_chat_history: list):
        """Test getting the last message from a specific role"""
        last_user_message = chat_history_manager.get_last_message(
            module_id=TEST_MODULE_ID,
            profile=TEST_PROFILE,
            role="user"
        )
        
        assert last_user_message is not None
        assert last_user_message["role"] == "user"
        assert last_user_message["content"] == "Tell me the weather"

    def test_get_last_message_not_found(self, chat_history_manager: ChatHistoryManager):
        """Test getting the last message when none exists"""
        # Use a module ID that doesn't exist
        last_message = chat_history_manager.get_last_message(
            module_id="nonexistent-module",
            profile=TEST_PROFILE
        )
        
        assert last_message is None

    def test_error_handling_get_history(self, chat_history_manager: ChatHistoryManager):
        """Test error handling when getting chat history fails"""
        # Make _db raise an exception when used as context manager
        def raise_exception(*args, **kwargs):
            raise Exception("Database error")
            
        # Create a mock context manager that raises an exception
        @contextmanager
        def mock_context_manager():
            raise Exception("Database error")
            yield None
            
        chat_history_manager._db = mock_context_manager()
        
        with pytest.raises(AgentError) as excinfo:
            chat_history_manager.get_chat_history(TEST_MODULE_ID, TEST_PROFILE)
            
        assert "Failed to get chat history" in str(excinfo.value)

    def test_error_handling_add_to_history(self, chat_history_manager: ChatHistoryManager):
        """Test error handling when adding to chat history fails"""
        # Create a mock context manager that raises an exception
        @contextmanager
        def mock_context_manager():
            raise Exception("Database error")
            yield None
            
        chat_history_manager._db = mock_context_manager()
        
        with pytest.raises(AgentError) as excinfo:
            chat_history_manager.add_to_history(
                module_id=TEST_MODULE_ID,
                profile=TEST_PROFILE,
                role="user",
                content="Test message"
            )
            
        assert "Failed to add to history" in str(excinfo.value)