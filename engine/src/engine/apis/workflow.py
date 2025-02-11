from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, insert

from engine.db.models import ChatHistory
from engine.db.session import SessionLocal
from engine.services.execution.workflow import WorkflowError, WorkflowService
from engine.config.workflow_config import WorkflowConfigService
from engine.utils.yaml import YAMLUtils
from engine.utils.logging import logger
from engine.services.execution.stage_state import StateService

class ExecuteStepRequest(BaseModel):
    """Request body for executing a workflow step"""
    parameters: Dict[str, Any] = {}

class CreateSessionResponse(BaseModel):
    """Response for session creation"""
    session_id: str
    timestamp: str

class WorkflowRouter:
    """FastAPI router for workflow operations"""
    
    def __init__(
        self,
        workflow_service: WorkflowService,
        prefix: str = "/workflow"
    ):
        self.service = workflow_service
        self.config_service = WorkflowConfigService()
        self.stage_state_service = StateService()
        self.router = APIRouter(prefix=prefix, tags=["workflow"])
        self._setup_routes()
    
    async def _create_session(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow type")
    ) -> CreateSessionResponse:
        """Create a new chat session"""
        try:
            session_id = str(uuid.uuid4())
            timestamp = datetime.now(UTC)
            
            # Add an initial system message to make the session appear in the list
            with SessionLocal() as db:
                stmt = insert(ChatHistory).values(
                    module_id=module_id,
                    section=workflow,
                    role="system",
                    content="Session created",
                    timestamp=timestamp,
                    message_type="text",
                    session_id=session_id
                )
                db.execute(stmt)
                db.commit()
            
            return CreateSessionResponse(
                session_id=session_id,
                timestamp=timestamp.isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def _get_workflows(
        self,
        module_id: str = Query(..., description="Module ID")
    ) -> List[Dict[str, Any]]:
        """
        Get all available workflows and their configurations for a module.
        
        This endpoint provides a comprehensive view of all workflows available for a module, including:
        - Base workflow configuration (type, agent, instructions, prerequisites)
        - Module-specific customizations from kit.yaml
        - Workflow metadata (instructions, steps, requirements)
        - Default available actions with their schemas
        
        Returns:
            List[Dict[str, Any]]: List of workflow configurations where each contains:
                - workflow_type: The type of workflow (initialize, maintain, etc)
                - agent_type: The type of agent that handles this workflow
                - base_instructions: Default instructions for this workflow
                - prerequisites: List of workflows that must be completed first
                - module_id: ID of the module
                - metadata: Workflow metadata including instructions and available steps
                - default_actions: List of actions available by default
                - kit_config: Module-specific configuration from kit.yaml
        """
        try:
            # Get module path to read kit.yaml
            module_path = self.service.module_service.get_module_path(module_id)
            kit = YAMLUtils.read_kit(module_path)
            
            # Log kit workflows for debugging
            logger.info(f"Kit workflows for module {module_id}:\n{kit.get('workflows', {})}")
            
            # Process each workflow
            workflow_configs = []
            
            for workflow_type in self.config_service.default_configs:
                try:
                    # Get kit workflow config first and ensure actions list
                    kit_workflow = kit.get('workflows', {}).get(workflow_type, {})
                    # Default empty actions list if not provided
                    if 'actions' not in kit_workflow:
                        kit_workflow['actions'] = []
                        
                    logger.info(f"""Processing workflow {workflow_type}:
                    Kit config: {kit_workflow}
                    """)
                    
                    # Get base config
                    config = self.config_service.get_workflow_config(
                        workflow_type=workflow_type,
                        kit_config=kit_workflow
                    )
                    
                    # Get workflow metadata
                    metadata = self.service.get_workflow_metadata(
                        module_id=module_id,
                        workflow=workflow_type
                    )
                    
                    # Get default actions
                    default_actions = []
                    for action in config.default_actions:
                        default_actions.append({
                            "name": action.name,
                            "description": action.description,
                            "schema": action.schema
                        })
                    
                    # Get workflow completion status
                    is_completed = self.stage_state_service.get_workflow_status(
                        module_id=module_id,
                        workflow_type=workflow_type
                    )
                    
                    # Only append if everything loaded successfully
                    workflow_configs.append({
                        "workflow_type": config.workflow_type,
                        "agent_type": config.agent_type,
                        "base_instructions": config.base_instructions,
                        "module_id": module_id,
                        "metadata": metadata,
                        "default_actions": default_actions,
                        "kit_config": kit_workflow,
                        "is_completed": is_completed,
                        "allow_multiple": config.allow_multiple
                    })
                    
                except Exception as e:
                    # Log error but continue processing other workflows
                    logger.error(f"""Failed to load workflow {workflow_type}:
                    Error: {str(e)}
                    Module: {module_id}
                    Kit config: {kit.get('workflows', {}).get(workflow_type)}
                    """)
                    # Skip this workflow rather than including with error
            
            return workflow_configs
            
        except Exception as e:
            logger.error(f"Failed to get workflows for module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_workflow_metadata(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow (initialize/maintain/remove/edit)"),
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> Dict[str, Any]:
        """
        Get workflow metadata including instructions and steps.

        This endpoint provides detailed information about a specific workflow, including:
        - Workflow instructions from the module's instructions directory
        - Available steps/actions with their metadata
        - Module requirements needed for the workflow
        
        Returns:
            Dict[str, Any]: Workflow metadata containing:
                - instructions: String containing workflow instructions
                - actions: List of available steps with metadata
                - requirements: List of module requirements
        """
        try:
            metadata = self.service.get_workflow_metadata(
                module_id=module_id,
                workflow=workflow
            )
            return metadata
        except WorkflowError as e:
            logger.error(f"Failed to get metadata for workflow {workflow} in module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _execute_workflow_step(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow (initialize/maintain/remove/edit)"),
        step_name: str = Query(..., description="Name of the step to execute"),
        request: ExecuteStepRequest = None,
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> Dict[str, Any]:
        """
        Execute a workflow step with provided parameters.

        This endpoint executes a specific step in a workflow. The step must be available
        in the workflow's configuration. Parameters for the step can be provided in the
        request body.

        If no parameters are provided, an empty parameter set will be used.
        
        Returns:
            Dict[str, Any]: Execution result containing:
                - result: The result of the execution
                May also include error details if execution fails
        """
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
            logger.error(f"Failed to execute step {step_name} in workflow {workflow} for module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_workflow_sessions(
        self,
        module_id: str = Query(..., description="Module ID"),
        workflow: str = Query(..., description="Workflow type")
    ) -> List[Dict[str, Any]]:
        """
        Get all available sessions for a workflow.
        
        Returns a list of sessions including their IDs and latest messages.
        """
        try:
            with SessionLocal() as db:
                # Get all unique session IDs for this module/workflow
                stmt = (
                    select(ChatHistory.session_id)
                    .distinct()
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.section == workflow
                    )
                )
                sessions = db.execute(stmt).scalars().all()
                
                # Get latest message for each session
                result = []
                for session_id in sessions:
                    latest_msg = (
                        db.query(ChatHistory)
                        .filter(
                            ChatHistory.module_id == module_id,
                            ChatHistory.section == workflow,
                            ChatHistory.session_id == session_id
                        )
                        .order_by(ChatHistory.timestamp.desc())
                        .first()
                    )
                    
                    if latest_msg:
                        result.append({
                            "session_id": session_id,
                            "last_message": latest_msg.content,
                            "last_updated": latest_msg.timestamp.isoformat(),
                            "is_default": session_id == str(uuid.UUID(int=0))
                        })
                
                return sorted(result, key=lambda x: x["last_updated"], reverse=True)
                
        except Exception as e:
            logger.error(f"Failed to get workflow sessions: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/session/create",
            self._create_session,
            methods=["POST"],
            response_model=CreateSessionResponse,
            summary="Create a new chat session",
            description="Create a new chat session for a workflow"
        )

        self.router.add_api_route(
            "/metadata",
            self._get_workflow_metadata,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Get detailed metadata for a specific workflow",
            description="Get workflow-specific information including instructions, available steps, and requirements"
        )

        self.router.add_api_route(
            "/sessions",
            self._get_workflow_sessions,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="Get all available sessions for a workflow",
            description="Get list of chat sessions including their IDs and latest messages"
        )

        self.router.add_api_route(
            "/execute",
            self._execute_workflow_step,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Execute a specific step in a workflow",
            description="Execute a workflow step with optional parameters provided in the request body"
        )

        self.router.add_api_route(
            "/workflows",
            self._get_workflows,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="Get all available workflows for a module",
            description="Get comprehensive configuration for all workflows including base config, metadata, and module customizations"
        )
