# engine/apis/coder.py

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.services.agents.base_agent import AgentError, AgentServices, AgentContext
from engine.services.agents.coder_agent import CoderAgent

class CodeEditRequest(BaseModel):
    """Request model for code editing"""
    input: str

class CodeEditResponse(BaseModel):
    """Response model for code editing"""
    response: str
    results: List[Dict[str, Any]]

class CoderRouter:
    """FastAPI router for code editing endpoints"""

    def __init__(
        self,
        agent_services: AgentServices,
        prefix: str = "/coder"
    ):
        self.agent = CoderAgent(agent_services)
        self.router = APIRouter(prefix=prefix, tags=["coder"])
        self._setup_routes()

    async def _process_edit(
        self,
        module_id: str,
        request: CodeEditRequest
    ) -> CodeEditResponse:
        """Handle code edit request"""
        try:
            context = AgentContext(
                module_id=module_id,
                workflow="edit",  # Coder agent always uses edit workflow
                user_input=request.input
            )
            
            result = await self.agent.process_request(context)
            return CodeEditResponse(
                response=result["response"],
                results=result.get("results", [])
            )
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_edit_history(
        self,
        module_id: str
    ) -> Dict[str, Any]:
        """Get edit history for a module"""
        try:
            history = self.agent.history_manager.get_chat_history(
                module_id=module_id,
                workflow="edit"
            )
            return {
                "history": history,
                "module_id": module_id
            }
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _setup_routes(self):
        """Setup API routes"""
        self.router.add_api_route(
            "/{module_id}/edit",
            self._process_edit,
            methods=["POST"],
            response_model=CodeEditResponse
        )

        self.router.add_api_route(
            "/{module_id}/history",
            self._get_edit_history,
            methods=["GET"],
            response_model=Dict[str, Any]
        )