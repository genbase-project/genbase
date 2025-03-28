from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, insert

from engine.db.models import ChatHistory
from engine.db.session import SessionLocal
from engine.services.execution.profile import ProfileError, ProfileService
from engine.config.profile_config import ProfileConfigService
from engine.utils.yaml import YAMLUtils
from loguru import logger
from engine.services.execution.state import StateService

class ExecuteStepRequest(BaseModel):
    """Request body for executing a profile step"""
    parameters: Dict[str, Any] = {}

class CreateSessionResponse(BaseModel):
    """Response for session creation"""
    session_id: str
    timestamp: str

class ProfileRouter:
    """FastAPI router for profile operations"""
    
    def __init__(
        self,
        profile_service: ProfileService,
        prefix: str = "/profile"
    ):
        self.service = profile_service
        self.config_service = ProfileConfigService()
        self.stage_state_service = StateService()
        self.router = APIRouter(prefix=prefix, tags=["profile"])
        self._setup_routes()
    
    async def _create_session(
        self,
        module_id: str = Query(..., description="Module ID"),
        profile: str = Query(..., description="Profile type")
    ) -> CreateSessionResponse:
        """Create a new chat session"""
        try:
            session_id = str(uuid.uuid4())
            timestamp = datetime.now(UTC)
            
            # Add an initial system message to make the session appear in the list
            with SessionLocal() as db:
                stmt = insert(ChatHistory).values(
                    module_id=module_id,
                    profile=profile,
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
    
    async def _get_profiles(
        self,
        module_id: str = Query(..., description="Module ID")
    ) -> List[Dict[str, Any]]:
        """
        Get all available profiles and their configurations for a module.
        
        This endpoint provides a comprehensive view of all profiles available for a module, including:
        - Base profile configuration (type, agent, instructions, prerequisites)
        - Module-specific customizations from kit.yaml
        - Profile metadata (instructions, steps, requirements)
        - Default available actions with their schemas
        
        Returns:
            List[Dict[str, Any]]: List of profile configurations where each contains:
                - profile_type: The type of profile (initialize, maintain, etc)
                - agent_type: The type of agent that handles this profile
                - base_instructions: Default instructions for this profile
                - prerequisites: List of profiles that must be completed first
                - module_id: ID of the module
                - metadata: Profile metadata including instructions and available steps
                - default_actions: List of actions available by default
                - kit_config: Module-specific configuration from kit.yaml
        """
        try:
            # Get module path to read kit.yaml
            module_path = self.service.module_service.get_module_path(module_id)
            kit = YAMLUtils.read_kit(module_path)
            
            # Log kit profiles for debugging
            logger.info(f"Kit profiles for module {module_id}:\n{kit.get('profiles', {})}")
            
            # Process each profile
            profile_configs = []

            profile_list = list(kit.get('profiles', {}).keys())

            
            for profile_type in profile_list:
                try:
                    # Get kit profile config first and ensure actions list
                    kit_profile = kit.get('profiles', {}).get(profile_type, {})
                    # Default empty actions list if not provided
                    if 'actions' not in kit_profile:
                        kit_profile['actions'] = []
                        
                    logger.info(f"""Processing profile {profile_type}:
                    Kit config: {kit_profile}
                    """)
                    
                    # Get base config
                    config = self.config_service.get_profile_config(
                        profile_type=profile_type,
                        kit_config=kit_profile
                    )
                    
                    # Get profile metadata
                    metadata = self.service.get_profile_metadata(
                        module_id=module_id,
                        profile=profile_type
                    )
                    
                    # Get default actions
                    default_actions = []
                    for action in config.default_actions:
                        default_actions.append({
                            "name": action.name,
                            "description": action.description,
                            "schema": action.schema
                        })
                    
                    # Get profile completion status
                    is_completed = self.stage_state_service.get_profile_status(
                        module_id=module_id,
                        profile_type=profile_type
                    )
                    
                    # Only append if everything loaded successfully
                    profile_configs.append({
                        "profile_type": config.profile_type,
                        "agent_type": config.agent_type,
                        "base_instructions": config.base_instructions,
                        "module_id": module_id,
                        "metadata": metadata,
                        "default_actions": default_actions,
                        "kit_config": kit_profile,
                        "is_completed": is_completed,
                        "allow_multiple": config.allow_multiple
                    })
                    
                except Exception as e:
                    # Log error but continue processing other profiles
                    logger.error(f"""Failed to load profile {profile_type}:
                    Error: {str(e)}
                    Module: {module_id}
                    Kit config: {kit.get('profiles', {}).get(profile_type)}
                    """)
                    # Skip this profile rather than including with error
            
            return profile_configs
            
        except Exception as e:
            logger.error(f"Failed to get profiles for module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_profile_metadata(
        self,
        module_id: str = Query(..., description="Module ID"),
        profile: str = Query(..., description="Profile (initialize/maintain/remove/edit)"),
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> Dict[str, Any]:
        """
        Get profile metadata including instructions and steps.

        This endpoint provides detailed information about a specific profile, including:
        - profile instructions from the module's instructions directory
        - Available steps/actions with their metadata
        - Module requirements needed for the profile
        
        Returns:
            Dict[str, Any]: profile metadata containing:
                - instructions: String containing profile instructions
                - actions: List of available steps with metadata
                - requirements: List of module requirements
        """
        try:
            metadata = self.service.get_profile_metadata(
                module_id=module_id,
                profile=profile
            )
            return metadata
        except ProfileError as e:
            logger.error(f"Failed to get metadata for profile {profile} in module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _execute_profile_action(
        self,
        module_id: str = Query(..., description="Module ID"),
        profile: str = Query(..., description="profile (initialize/maintain/remove/edit)"),
        step_name: str = Query(..., description="Name of the step to execute"),
        request: ExecuteStepRequest = None,
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> Dict[str, Any]:
        """
        Execute a profile step with provided parameters.

        This endpoint executes a specific step in a profile. The step must be available
        in the profile's configuration. Parameters for the step can be provided in the
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

            result = self.service.execute_profile_action(
                action_name=step_name,
                parameters=request.parameters
            )
            return {"result": result}
        except ProfileError as e:
            logger.error(f"Failed to execute step {step_name} in profile {profile} for module {module_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def _get_profile_sessions(
        self,
        module_id: str = Query(..., description="Module ID"),
        profile: str = Query(..., description="Profile type")
    ) -> List[Dict[str, Any]]:
        """
        Get all available sessions for a Profile.
        
        Returns a list of sessions including their IDs and latest messages.
        """
        try:
            with SessionLocal() as db:
                # Get all unique session IDs for this module/profile
                stmt = (
                    select(ChatHistory.session_id)
                    .distinct()
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.profile == profile
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
                            ChatHistory.profile == profile,
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
            logger.error(f"Failed to get profile sessions: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route(
            "/session/create",
            self._create_session,
            methods=["POST"],
            response_model=CreateSessionResponse,
            summary="Create a new chat session",
            description="Create a new chat session for a profile"
        )

        self.router.add_api_route(
            "/metadata",
            self._get_profile_metadata,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Get detailed metadata for a specific profile",
            description="Get profile-specific information including instructions, available steps, and requirements"
        )

        self.router.add_api_route(
            "/sessions",
            self._get_profile_sessions,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="Get all available sessions for a profile",
            description="Get list of chat sessions including their IDs and latest messages"
        )

        self.router.add_api_route(
            "/execute",
            self._execute_profile_action,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Execute a specific step in a profile",
            description="Execute a profile step with optional parameters provided in the request body"
        )

        self.router.add_api_route(
            "/profiles",
            self._get_profiles,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="Get all available profiles for a module",
            description="Get comprehensive configuration for all profiles including base config, metadata, and module customizations"
        )
