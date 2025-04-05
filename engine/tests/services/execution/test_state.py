# tests/services/execution/test_state.py

import pytest
from unittest.mock import patch
from datetime import datetime, UTC, timedelta
from contextlib import contextmanager

from sqlalchemy.orm import Session

from engine.services.execution.state import StateService, AgentState, InvalidTransition
from engine.db.models import AgentStatus, ProfileStatus

# --- Constants ---
TEST_MODULE_ID = "test-module-123"
TEST_PROFILE_TYPE = "test-profile"

# --- Fixtures ---

@pytest.fixture
def state_service(db_session: Session) -> StateService:
    service = StateService()
    
    @contextmanager
    def test_db_context():
        try:
            yield db_session
        finally:
            pass
    
    service._get_db = test_db_context
    return service

@pytest.fixture
def initialized_module(state_service: StateService, db_session: Session) -> str:
    """Initialize a test module and return its ID"""
    state_service.initialize_module(TEST_MODULE_ID)
    return TEST_MODULE_ID

@pytest.fixture
def profile_status(db_session: Session, initialized_module: str) -> ProfileStatus:
    """Create a profile status entry for testing"""
    status = ProfileStatus(
        module_id=initialized_module,
        profile_type=TEST_PROFILE_TYPE,
        is_completed=False,
        last_updated=datetime.now(UTC)
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status

# --- Test Cases ---

class TestStateService:

    def test_initialize_module(self, state_service: StateService, db_session: Session):
        """Test initializing a module sets the correct initial state"""
        module_id = "new-module-456"
        state_service.initialize_module(module_id)
        
        # Verify in database
        status = db_session.query(AgentStatus).filter_by(module_id=module_id).first()
        assert status is not None
        assert status.state == AgentState.STANDBY.value
        assert status.last_updated is not None

    def test_get_status_existing(self, state_service: StateService, initialized_module: str):
        """Test getting status for an existing module"""
        state = state_service.get_status(initialized_module)
        assert state == AgentState.STANDBY

    def test_get_status_nonexistent(self, state_service: StateService, db_session: Session):
        """Test getting status for a nonexistent module initializes it"""
        module_id = "nonexistent-module"
        
        # Verify module doesn't exist yet
        status_before = db_session.query(AgentStatus).filter_by(module_id=module_id).first()
        assert status_before is None
        
        # Get status should initialize it
        state = state_service.get_status(module_id)
        assert state == AgentState.STANDBY
        
        # Verify it was created
        status_after = db_session.query(AgentStatus).filter_by(module_id=module_id).first()
        assert status_after is not None
        assert status_after.state == AgentState.STANDBY.value

    def test_set_executing(self, state_service: StateService, initialized_module: str, db_session: Session):
        """Test setting state to executing"""
        state_service.set_executing(initialized_module)
        
        # Verify in database
        status = db_session.query(AgentStatus).filter_by(module_id=initialized_module).first()
        assert status.state == AgentState.EXECUTING.value

    def test_set_standby(self, state_service: StateService, initialized_module: str, db_session: Session):
        """Test setting state to standby"""
        # First set to executing
        state_service.set_executing(initialized_module)
        
        # Then back to standby
        state_service.set_standby(initialized_module)
        
        # Verify in database
        status = db_session.query(AgentStatus).filter_by(module_id=initialized_module).first()
        assert status.state == AgentState.STANDBY.value

    def test_state_transitions(self, state_service: StateService, initialized_module: str):
        """Test all valid state transitions"""
        # Start in STANDBY (from initialization)
        assert state_service.get_status(initialized_module) == AgentState.STANDBY
        
        # STANDBY -> EXECUTING
        state_service.set_executing(initialized_module)
        assert state_service.get_status(initialized_module) == AgentState.EXECUTING
        
        # EXECUTING -> STANDBY
        state_service.set_standby(initialized_module)
        assert state_service.get_status(initialized_module) == AgentState.STANDBY


    def test_get_last_updated_nonexistent(self, state_service: StateService, db_session: Session):
        """Test getting last updated for a nonexistent module initializes it"""
        module_id = "another-nonexistent-module"
        
        # Verify module doesn't exist yet
        status_before = db_session.query(AgentStatus).filter_by(module_id=module_id).first()
        assert status_before is None
        
        # Get last updated should initialize it and return current time
        last_updated = state_service.get_last_updated(module_id)
        
        # Parse the returned ISO time string
        update_time = datetime.fromisoformat(last_updated)
        
        # Should be very recent (within the last second)
        time_diff = datetime.now(UTC) - update_time
        assert time_diff < timedelta(seconds=1)
        
        # Verify module was created
        status_after = db_session.query(AgentStatus).filter_by(module_id=module_id).first()
        assert status_after is not None

    def test_get_profile_status_nonexistent(self, state_service: StateService, initialized_module: str):
        """Test getting profile status for nonexistent profile returns False"""
        is_completed = state_service.get_profile_status(initialized_module, "nonexistent-profile")
        assert is_completed is False

    def test_get_profile_status_incomplete(self, state_service: StateService, profile_status: ProfileStatus):
        """Test getting incomplete profile status returns False"""
        is_completed = state_service.get_profile_status(TEST_MODULE_ID, TEST_PROFILE_TYPE)
        assert is_completed is False

    def test_get_profile_status_complete(self, state_service: StateService, profile_status: ProfileStatus, db_session: Session):
        """Test getting complete profile status returns True"""
        # Update profile to completed
        profile_status.is_completed = True
        db_session.commit()
        
        is_completed = state_service.get_profile_status(TEST_MODULE_ID, TEST_PROFILE_TYPE)
        assert is_completed is True