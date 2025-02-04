# from typing import Any, Dict

# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel

# from engine.services.execution.agent import AgentError, AgentService


# class WorkflowExecuteRequest(BaseModel):
#     """Request model for workflow execution"""
#     section: str
#     input: str

# class MessageRequest(BaseModel):
#     """Request model for sending messages"""
#     message: str

# class StatusResponse(BaseModel):
#     """Response model for module status"""
#     module_id: str
#     stage: str
#     state: str
#     last_updated: str



# class AgentRouter:
#     """FastAPI router for AI workflow endpoints"""

#     def __init__(
#         self,
#         agent_service: AgentService,
#         prefix: str = "/agent"
#     ):
#         self.service = agent_service
#         self.router = APIRouter(prefix=prefix, tags=["agent"])
#         self._setup_routes()

#     async def _execute_workflow(
#         self,
#         module_id: str,
#         request: WorkflowExecuteRequest
#     ) -> Dict[str, Any]:
#         """Handle workflow execution request"""
#         try:
#             response = await self.service.execute_agent_workflow(
#                 module_id=module_id,
#                 workflow=request.section,
#                 user_input=request.input
#             )
#             return response
#         except AgentError as e:
#             raise HTTPException(status_code=400, detail=str(e))
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))


#     async def _clear_history(self, module_id: str):
#         """Handle clear history request"""
#         try:
#             self.service.clear_history(module_id)
#             return {"status": "success"}
#         except AgentError as e:
#             raise HTTPException(status_code=400, detail=str(e))
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#     async def _get_section_history(
#         self,
#         module_id: str,
#         section: str
#     ) -> Dict[str, Any]:
#         """Handle get section history request"""
#         try:
#             history = self.service.get_workflow_history(
#                 module_id=module_id,
#                 workflow=section
#             )
#             return {
#                 "history": history,
#                 "section": section,
#                 "module_id": module_id
#             }
#         except AgentError as e:
#             raise HTTPException(status_code=400, detail=str(e))
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))




#     async def _get_status(self, module_id: str) -> StatusResponse:
#         """Get current stage and state for a module"""
#         try:
#             status = self.service.get_module_status(module_id)
#             return StatusResponse(
#                 module_id=module_id,
#                 stage=status["stage"],
#                 state=status["state"],
#                 last_updated=status["last_updated"]
#             )
#         except AgentError as e:
#             raise HTTPException(status_code=400, detail=str(e))
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#     def _setup_routes(self):
#         """Setup API routes"""
#         self.router.add_api_route(
#             "/{module_id}/execute",
#             self._execute_workflow,
#             methods=["POST"],
#             response_model=Dict[str, Any]
#         )



#         self.router.add_api_route(
#             "/{module_id}/history",
#             self._clear_history,
#             methods=["DELETE"],
#             response_model=Dict[str, Any]
#         )

#         self.router.add_api_route(
#             "/{module_id}/sections/{section}/history",
#             self._get_section_history,
#             methods=["GET"],
#             response_model=Dict[str, Any]
#         )


#         # Add new status endpoint
#         self.router.add_api_route(
#             "/{module_id}/status",
#             self._get_status,
#             methods=["GET"],
#             response_model=StatusResponse
#         )

