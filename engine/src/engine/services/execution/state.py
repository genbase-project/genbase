from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from engine.db.models import AgentStatus, ProfileStatus
from engine.db.session import SessionLocal




class AgentState(Enum):
    STANDBY = "STANDBY"
    EXECUTING = "EXECUTING"

class InvalidTransition(Exception):
    """Exception for invalid stage/state transitions"""
    pass

class StateService:
    def _get_db(self) -> Session:
        return SessionLocal()


    def initialize_module(self, module_id: str):
        """Set up initial stage and state for new module"""
        with self._get_db() as db:
            status = AgentStatus(
                module_id=module_id,
                stage="INITIALIZE",
                state=AgentState.STANDBY.value,
                last_updated=datetime.now(UTC)
            )
            db.merge(status)  # merge instead of add to handle both insert and update
            db.commit()

    def get_status(self, module_id: str) -> tuple[Any, AgentState]:
        """Get current stage and state"""
        with self._get_db() as db:
            stmt = select(AgentStatus).where(AgentStatus.module_id == module_id)
            status = db.execute(stmt).scalar_one_or_none()

            if status is None:
                # Initialize if not exists
                self.initialize_module(module_id)
                return "INITIALIZE", AgentState.STANDBY

            return "INITIALIZE", AgentState(status.state)


    def set_executing(self, module_id: str):
        """Set state to executing"""
        with self._get_db() as db:
            status = db.query(AgentStatus).filter_by(module_id=module_id).first()
            if status:
                status.state = AgentState.EXECUTING.value
                status.last_updated = datetime.now(UTC)
                db.commit()

    def set_standby(self, module_id: str):
        """Set state back to standby"""
        with self._get_db() as db:
            status = db.query(AgentStatus).filter_by(module_id=module_id).first()
            if status:
                status.state = AgentState.STANDBY.value
                status.last_updated = datetime.now(UTC)
                db.commit()

    def get_last_updated(self, module_id: str) -> str:
        """Get timestamp of last status update"""
        with self._get_db() as db:
            stmt = select(AgentStatus).where(AgentStatus.module_id == module_id)
            status = db.execute(stmt).scalar_one_or_none()
            
            if status is None:
                self.initialize_module(module_id)
                return datetime.now(UTC).isoformat()
            
            return status.last_updated.isoformat()


       
    def get_profile_status(self, module_id: str, profile_type: str) -> bool:
        """Get completion status for a profile"""
        with self._get_db() as db:
            stmt = select(ProfileStatus).where(
                ProfileStatus.module_id == module_id,
                ProfileStatus.profile_type == profile_type
            )
            status = db.execute(stmt).scalar_one_or_none()
            
            return bool(status and status.is_completed)
