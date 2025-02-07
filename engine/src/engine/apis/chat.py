# engine/apis/agent.py

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from engine.config.workflow_config import WorkflowConfigurations
from engine.services.agents.base_agent import BaseAgent
from engine.services.agents.base_agent import AgentError, AgentServices, AgentContext
from engine.services.agents.tasker import TaskerAgent
from engine.services.agents.coder_agent import CoderAgent
from engine.config.workflow_config import WorkflowConfigService

class WorkflowExecuteRequest(BaseModel):
    """Request model for workflow execution"""
    section: str
    input: str
    session_id: str = "00000000-0000-0000-0000-000000000000"  # Default UUID(0)

class WorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    response: str
    results: List[Dict[str, Any]]

class HistoryResponse(BaseModel):
    """Response model for history"""
    history: List[Dict[str, Any]]
    section: str
    module_id: str

class StatusResponse(BaseModel):
    """Response model for module status"""
    module_id: str
    stage: str
    state: str
    last_updated: str

class ChatRouter:
    """FastAPI router for agent endpoints"""

    def __init__(
        self,
        agent_services: AgentServices,
        prefix: str = "/chat"
    ):
        self.services = agent_services
        self.workflow_config_service = WorkflowConfigService()
        
        # Initialize agents
        self.tasker_agent = TaskerAgent(agent_services)
        self.coder_agent = CoderAgent(agent_services)
        
        # Important: prefix is /chat in our route declarations
        self.router = APIRouter(prefix=prefix, tags=["agent"])
        self._setup_routes()

    def _get_agent_for_workflow(self, workflow_type: str) -> BaseAgent:
        """Get appropriate agent based on workflow type"""
        try:
            config = self.workflow_config_service.get_workflow_config(workflow_type)
            
            if config.agent_type == WorkflowConfigurations.TASKER_AGENT:
                return self.tasker_agent
            elif config.agent_type == WorkflowConfigurations.CODER_AGENT:
                return self.coder_agent
            else:
                raise AgentError(f"Unknown agent type for workflow: {workflow_type}")
                
        except Exception as e:
            raise AgentError(f"Failed to determine agent type: {str(e)}")

    async def _execute_workflow(
        self,
        request: WorkflowExecuteRequest,
        module_id: str = Path(..., description="Module ID")
    ) -> WorkflowResponse:
        """Handle workflow execution request"""
        try:
            # Get appropriate agent
            agent = self._get_agent_for_workflow(request.section)
            
            # Create context
            context = AgentContext(
                module_id=module_id,
                workflow=request.section,
                user_input=request.input,
                session_id=request.session_id
            )
            
            # Execute workflow
            result = await agent.process_request(context)
            
            return WorkflowResponse(
                response=result["response"],
                results=result.get("results", [])
            )
            
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_workflow_history(
        self,
        module_id: str = Path(..., description="Module ID"),
        workflow: str = Path(..., description="Workflow (initialize/maintain/remove/edit)"),
        session_id: Optional[str] = Query("00000000-0000-0000-0000-000000000000", description="Optional session ID")
    ) -> HistoryResponse:
        """Get workflow history"""
        try:
            # Get appropriate agent
            agent = self._get_agent_for_workflow(workflow)
            
            history = agent.history_manager.get_chat_history(
                module_id=module_id,
                workflow=workflow,
                session_id=session_id
            )
            
            return HistoryResponse(
                history=history,
                section=workflow,
                module_id=module_id
            )
            
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_status(
        self,
        module_id: str = Path(..., description="Module ID")
    ) -> StatusResponse:
        """Get module status"""
        try:
            stage, state = self.services.stage_state_service.get_status(module_id)
            last_updated = self.services.stage_state_service.get_last_updated(module_id)
            
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
        # Update parameter description to clarify session_id usage
        descriptions = {
            "module_id": "Module ID",
            "section": "Workflow section (initialize/maintain/remove/edit)",
            "session_id": "Optional session ID. Defaults to base session if not provided."
        }
        
        # Use full paths with /chat prefix since it's not in router prefix
        self.router.add_api_route(
            "/{module_id}/execute",
            self._execute_workflow,
            methods=["POST"],
            response_model=WorkflowResponse
        )

        self.router.add_api_route(
            "/{module_id}/workflow/{workflow}/history",
            self._get_workflow_history,
            methods=["GET"],
            response_model=HistoryResponse
        )

        self.router.add_api_route(
            "/{module_id}/status",
            self._get_status,
            methods=["GET"],
            response_model=StatusResponse
        )
