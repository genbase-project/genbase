from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from engine.db.models import AgentStatus, WorkflowStatus
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


    def complete_workflow(self, module_id: str, workflow_type: str) -> Dict[str, Any]:
        """Mark a workflow as completed"""

        with SessionLocal() as db:
            # Try to update existing record
            stmt = (
                update(WorkflowStatus)
                .where(
                    WorkflowStatus.module_id == module_id,
                    WorkflowStatus.workflow_type == workflow_type
                )
                .values(
                    is_completed=True,
                    last_updated=datetime.now(UTC)
                )
            )
            result = db.execute(stmt)
            
            # If no record exists, insert new one
            if result.rowcount == 0:
                workflow_status = WorkflowStatus(
                    module_id=module_id,
                    workflow_type=workflow_type,
                    is_completed=True,
                    last_updated=datetime.now(UTC)
                )
                db.add(workflow_status)
            
            db.commit()
            
            return {
                "status": "success", 
                "message": f"Workflow {workflow_type} marked as completed"
            }
            
    def get_workflow_status(self, module_id: str, workflow_type: str) -> bool:
        """Get completion status for a workflow"""
        with self._get_db() as db:
            stmt = select(WorkflowStatus).where(
                WorkflowStatus.module_id == module_id,
                WorkflowStatus.workflow_type == workflow_type
            )
            status = db.execute(stmt).scalar_one_or_none()
            
            return bool(status and status.is_completed)
