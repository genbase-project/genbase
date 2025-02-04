# engine/apis/tasker.py

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.services.agents.tasker import TaskerAgent
from engine.services.agents.base_agent import AgentError, AgentServices, AgentContext

class WorkflowExecuteRequest(BaseModel):
    """Request model for workflow execution"""
    section: str
    input: str

class MessageRequest(BaseModel):
    """Request model for sending messages"""
    message: str

class StatusResponse(BaseModel):
    """Response model for module status"""
    module_id: str
    stage: str
    state: str
    last_updated: str

class TaskerRouter:
    """FastAPI router for Tasker Agent endpoints"""

    def __init__(
        self,
        agent_services: AgentServices,
        prefix: str = "/tasker"
    ):
        self.agent = TaskerAgent(agent_services)
        self.router = APIRouter(prefix=prefix, tags=["tasker"])
        self._setup_routes()

    async def _execute_workflow(
        self,
        module_id: str,
        request: WorkflowExecuteRequest
    ) -> Dict[str, Any]:
        """Handle workflow execution request"""
        try:
            context = AgentContext(
                module_id=module_id,
                workflow=request.section,
                user_input=request.input
            )
            
            response = await self.agent.process_request(context)
            return response
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_section_history(
        self,
        module_id: str,
        section: str
    ) -> Dict[str, Any]:
        """Handle get section history request"""
        try:
            history = self.agent.history_manager.get_chat_history(
                module_id=module_id,
                workflow=section
            )
            return {
                "history": history,
                "section": section,
                "module_id": module_id
            }
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_status(self, module_id: str) -> StatusResponse:
        """Get current stage and state for a module"""
        try:
            stage, state = self.agent.services.stage_state_service.get_status(module_id)
            last_updated = self.agent.services.stage_state_service.get_last_updated(module_id)
            return StatusResponse(
                module_id=module_id,
                stage=stage.value,
                state=state.value,
                last_updated=last_updated
            )
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _setup_routes(self):
        """Setup API routes"""
        self.router.add_api_route(
            "/{module_id}/execute",
            self._execute_workflow,
            methods=["POST"],
            response_model=Dict[str, Any]
        )

        self.router.add_api_route(
            "/{module_id}/sections/{section}/history",
            self._get_section_history,
            methods=["GET"],
            response_model=Dict[str, Any]
        )

        self.router.add_api_route(
            "/{module_id}/status",
            self._get_status,
            methods=["GET"],
            response_model=StatusResponse
        )