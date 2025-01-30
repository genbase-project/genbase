from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from engine.services.execution.workflow import WorkflowError, WorkflowService


class ExecuteStepRequest(BaseModel):
    """Request body for executing a workflow step"""
    parameters: Dict[str, Any] = {}

class WorkflowRouter:
    """FastAPI router for workflow operations"""

    def __init__(
        self,
        workflow_service: WorkflowService,
        prefix: str = "/workflow"
    ):
        self.service = workflow_service
        self.router = APIRouter(prefix=prefix, tags=["workflow"])
        self._setup_routes()

    async def _get_workflow_metadata(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow (initialize/maintain/remove)")
    ) -> Dict[str, Any]:
        """Get workflow metadata including instructions and steps"""
        try:
            return self.service.get_workflow_metadata(
                module_id=module_id,
                workflow=workflow
            )
        except WorkflowError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def _execute_workflow_step(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow (initialize/maintain/remove)"),
        step_name: str = Query(..., description="Name of the step to execute"),
        request: ExecuteStepRequest = None
    ) -> Dict[str, Any]:
        """Execute a workflow step"""
        try:
            if request is None:
                request = ExecuteStepRequest()

            result = self.service.execute_workflow_step(
                module_id=module_id,
                workflow=workflow,
                action_name=step_name,
                parameters=request.parameters
            )
            return {"result": result}
        except WorkflowError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/metadata",
            self._get_workflow_metadata,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Get workflow metadata including instructions and steps"
        )

        self.router.add_api_route(
            "/execute",
            self._execute_workflow_step,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Execute workflow step"
        )
