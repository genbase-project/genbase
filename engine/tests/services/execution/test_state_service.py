# tests/services/execution/test_stage_state.py
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch
from engine.services.execution.stage_state import (
    StateService, AgentStage, AgentState, InvalidTransition
)

@pytest.fixture
def mock_db_session():
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    return session

@pytest.fixture
def stage_service():
    return StateService()

def test_validate_stage_transition(stage_service):
    """Test basic stage transition validation"""
    # Valid transitions
    assert stage_service._validate_stage_transition(AgentStage.INITIALIZE, AgentStage.MAINTAIN)
    assert stage_service._validate_stage_transition(AgentStage.MAINTAIN, AgentStage.REMOVE)
    
    # Invalid transitions
    assert not stage_service._validate_stage_transition(AgentStage.INITIALIZE, AgentStage.REMOVE)
    assert not stage_service._validate_stage_transition(AgentStage.REMOVE, AgentStage.MAINTAIN)

def test_initialize_module(stage_service, mock_db_session):
    """Test module initialization"""
    with patch('engine.services.execution.stage_state.SessionLocal', return_value=mock_db_session):
        stage_service.initialize_module("test-module")
        mock_db_session.merge.assert_called_once()
        mock_db_session.commit.assert_called_once()

def test_promote_stage(stage_service, mock_db_session):
    """Test stage promotion"""
    mock_status = Mock(stage=AgentStage.INITIALIZE.value)
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_status
    
    with patch('engine.services.execution.stage_state.SessionLocal', return_value=mock_db_session):
        # Set up get_status mock
        with patch.object(stage_service, 'get_status', return_value=(AgentStage.INITIALIZE, AgentState.STANDBY)):
            stage_service.promote_stage("test-module", AgentStage.MAINTAIN)
            assert mock_status.stage == AgentStage.MAINTAIN.value

def test_invalid_promotion(stage_service, mock_db_session):
    """Test invalid stage promotion"""
    with patch('engine.services.execution.stage_state.SessionLocal', return_value=mock_db_session):
        with patch.object(stage_service, 'get_status', return_value=(AgentStage.INITIALIZE, AgentState.STANDBY)):
            with pytest.raises(InvalidTransition):
                stage_service.promote_stage("test-module", AgentStage.REMOVE)

def test_set_executing(stage_service, mock_db_session):
    """Test setting executing state"""
    mock_status = Mock(state=AgentState.STANDBY.value)
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_status
    
    with patch('engine.services.execution.stage_state.SessionLocal', return_value=mock_db_session):
        stage_service.set_executing("test-module")
        assert mock_status.state == AgentState.EXECUTING.value