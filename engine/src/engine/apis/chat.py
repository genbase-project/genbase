# engine/apis/agent.py

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from engine.config.workflow_config import WorkflowConfigurations
from engine.services.agents.base_agent import BaseAgent
from engine.services.agents.base_agent import AgentServices, AgentContext
from engine.config.workflow_config import WorkflowConfigService

class WorkflowExecuteRequest(BaseModel):
    """Request model for workflow execution"""
    workflow: str
    input: str 
    session_id: Optional[str] = "00000000-0000-0000-0000-000000000000"  # Default UUID(0)

class WorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    response: str
    results: List[Dict[str, Any]]

class HistoryResponse(BaseModel):
    """Response model for history"""
    history: List[Dict[str, Any]]
    workflow: str
    module_id: str

class StatusResponse(BaseModel):
    """Response model for module status"""
    module_id: str
    state: str
    last_updated: str

from engine.services.agents.chat_history import AgentError
from engine.services.core.agent_loader import AgentLoader, AgentLoaderError

class ChatRouter:
    """FastAPI router for agent endpoints"""

    def __init__(
        self,
        agent_services: AgentServices,
        prefix: str = "/chat"
    ):
        self.services = agent_services
        self.workflow_config_service = WorkflowConfigService()
        self.agent_loader = AgentLoader(agent_services)
        
        # Important: prefix is /chat in our route declarations
        self.router = APIRouter(prefix=prefix, tags=["agent"])
        self._setup_routes()

    def _get_agent_for_workflow(self, workflow_type: str, module_id: str) -> BaseAgent:
        """Get appropriate agent based on workflow configuration in kit.yaml"""
        try:
            # Get module info
            module_path = self.services.module_service.get_module_path(module_id)
            
            # Get kit config first
            with open(module_path / "kit.yaml") as f:
                import yaml
                kit_config = yaml.safe_load(f)
            
            # Get workflow config
            config = self.workflow_config_service.get_workflow_config(workflow_type, kit_config)
            
            if not config.agent_type:
                raise AgentError(f"No agent type specified for workflow: {workflow_type}")

            # Load appropriate agent from kit
            agent = self.agent_loader.load_workflow_agent(
                kit_path=module_path,
                workflow_name=workflow_type,
                workflow_config=config
            )
            
            if not agent:
                raise AgentError(f"Failed to load agent '{config.agent_type}' for workflow: {workflow_type}")
                
            return agent
                
        except AgentLoaderError as e:
            raise AgentError(f"Failed to load agent: {str(e)}")
        except Exception as e:
            raise AgentError(f"Failed to determine agent: {str(e)}")

    async def _execute_workflow(
        self,
        request: WorkflowExecuteRequest,
        module_id: str = Path(..., description="Module ID")
    ) -> WorkflowResponse:
        """Handle workflow execution request"""
        try:

            # Create context - force string session ID
            session_id = request.session_id or "00000000-0000-0000-0000-000000000000"
            
            # Get appropriate agent
            agent = self._get_agent_for_workflow(request.workflow, module_id)
            

            context = AgentContext(
                module_id=module_id,
                workflow=request.workflow,
                user_input=request.input,
                session_id=session_id
            )
            
            # Execute workflow
            result = await agent.handle_request(context)
            
            return WorkflowResponse(
                response=result.get("response", ""),  # Default empty string 
                results=result.get("results", [])
            )
            
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _get_workflow_history(
        self,
        module_id: str = Path(..., description="Module ID"),
        workflow: str = Path(..., description="Workflow"),
        session_id: Optional[str] = Query("00000000-0000-0000-0000-000000000000", description="Optional session ID")
    ) -> HistoryResponse:
        """Get workflow history"""
        try:
            # Get appropriate agent
            agent = self._get_agent_for_workflow(workflow, module_id)
            
            history = agent.history_manager.get_chat_history(
                module_id=module_id,
                workflow=workflow,
                session_id=session_id
            )
            
            return HistoryResponse(
                history=history,
                workflow=workflow,
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
            stage, state = self.services.state_service.get_status(module_id)
            last_updated = self.services.state_service.get_last_updated(module_id)
            
            return StatusResponse(
                module_id=module_id,
                state=state.value,
                last_updated=last_updated
            )
            
        except AgentError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _setup_routes(self):
        """Setup API routes"""
        
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
