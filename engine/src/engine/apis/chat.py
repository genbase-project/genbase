# engine/apis/chat.py

import json
import asyncio
import uuid # For default session ID
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Query, Path, Request # Added Request for SSE
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from datetime import datetime, UTC # For SSE timestamp

# SSE Imports
from sse_starlette.sse import EventSourceResponse

# Engine Imports
from engine.db.models import ChatHistory # For SSE
from engine.db.session import SessionLocal # For SSE
from sqlalchemy import select, desc # For SSE timestamp query
# Core services needed by ChatRouter or passed to AgentRunnerService
from engine.services.agents.context import AgentContext
# Correct execution service import
from engine.services.agents.types import AgentServices
from engine.services.execution.agent_execution import AgentRunnerService, AgentRunnerError
# Core services if needed directly by history/status endpoints
from engine.services.core.module import ModuleService, ModuleError, ModuleMetadata
from engine.services.core.kit import KitService, KitError, KitNotFoundError, KitConfig
from engine.services.execution.state import StateService
# Import history manager for history/SSE endpoints
from engine.services.agents.chat_history import ChatHistoryManager, AgentError

# --- Pydantic Models ---

class ProfileExecuteRequest(BaseModel):
    profile: str
    input: str
    session_id: Optional[str] = None # Default handled in endpoint

class ProfileResponse(BaseModel):
    # Expects the dictionary returned by the agent's process_request
    response: str
    results: List[Dict[str, Any]]

class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    profile: str
    module_id: str

class StatusResponse(BaseModel):
    module_id: str
    state: str # Assuming state service returns string value
    last_updated: str

# --- Chat Router ---

class ChatRouter:
    """FastAPI router for agent endpoints using containerized execution via AgentRunnerService."""

    def __init__(
        self,
        agent_services: AgentServices, # Keep core services for status/history
        agent_runner_service: AgentRunnerService, # Inject the CORRECT execution service
        prefix: str = "/chat"
    ):
        self.services = agent_services # Contains module_service, state_service, etc.
        self.agent_runner_service = agent_runner_service # Store the runner service
        self.history_manager = ChatHistoryManager() # Instantiate for history/SSE
        self.router = APIRouter(prefix=prefix, tags=["agent"])
        self._setup_routes()


# Simplified version of ChatRouter's _execute_profile method

    async def _execute_profile(
        self,
        request: ProfileExecuteRequest,
        module_id: str = Path(..., description="Module ID")
    ) -> ProfileResponse:
        """Handle profile execution request using AgentRunnerService."""
        try:
            # Ensure a session ID exists (use default if None)
            session_id = request.session_id or str(uuid.UUID(int=0))

            # Create context
            context = AgentContext(
                module_id=module_id,
                profile=request.profile,
                user_input=request.input,
                session_id=session_id
            )

            # Update module state to EXECUTING
            try:
                self.services.state_service.set_executing(module_id)
            except Exception as e:
                logger.warning(f"Could not set state to EXECUTING: {e}")

            logger.info(f"Dispatching execution for profile '{request.profile}' on module '{module_id}' via AgentRunnerService.")
            
            try:
                # Call AgentRunnerService
                execution_result = self.agent_runner_service.execute_agent_profile(context=context)
                
                # Create a manual response to avoid any serialization issues
                response_text = "No response from agent"
                results_list = []
                
                if isinstance(execution_result, dict):
                    if "response" in execution_result:
                        response_text = str(execution_result["response"])
                    if "results" in execution_result and isinstance(execution_result["results"], list):
                        results_list = list(execution_result["results"])
                

                    
                # Return the ProfileResponse directly, using safe values
                return ProfileResponse(
                    response=response_text,
                    results=results_list
                )
                
            except Exception as e:
                logger.error(f"Error from AgentRunnerService: {str(e)}", exc_info=True)
                    
                # Generate a service unavailable response
                raise HTTPException(
                    status_code=503,
                    detail=f"Agent execution failed: {str(e)}"
                )

        except HTTPException:
            # Re-raise if already an HTTPException
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in _execute_profile: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )
        
        finally:
            # Ensure state is set to STANDBY if not already done
            try:
                self.services.state_service.set_standby(module_id)
            except Exception as e:
                logger.warning(f"Could not set state to STANDBY: {e}")
    # --- History, Status, Streaming Endpoints (Interact with Engine State/DB) ---










    async def _execute_profile_tool(
        self,
        request: Request,
        module_id: str = Path(..., description="Module ID"),
        profile: str = Path(..., description="Profile"),
        tool_name: str = Path(..., description="Tool/action name")
    ) -> JSONResponse:
        """
        Execute a specific tool/action from a profile.
        
        Args:
            request: The HTTP request (containing JSON parameters for the tool)
            module_id: The module ID
            profile: The profile name
            tool_name: The name of the tool/action to execute
            
        Returns:
            JSONResponse with the tool's execution result
        """
        try:
            # Parse request body as JSON parameters for the tool
            parameters = await request.json()
            
            logger.info(f"Executing tool '{tool_name}' from profile '{profile}' on module '{module_id}'")
            logger.debug(f"Tool parameters: {parameters}")
            
            # Use the agent_runner_service to execute the tool
            result = self.agent_runner_service.execute_agent_tool(
                module_id=module_id,
                profile=profile,
                tool_name=tool_name,
                parameters=parameters
            )
            
            # Return the tool's result
            return JSONResponse(
                content={
                    "status": "success",
                    "result": result
                }
            )
        
        except AgentRunnerError as e:
            logger.error(f"Error executing tool: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error executing tool: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": f"Internal server error: {str(e)}"
                }
            )
        







    async def _get_profile_history(
        self,
        module_id: str = Path(..., description="Module ID"),
        profile: str = Path(..., description="Profile"),
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> HistoryResponse:
        """Get profile history (accesses engine DB directly)."""
        try:
            effective_session_id = session_id or str(uuid.UUID(int=0))
            # Use the history manager instantiated in __init__
            history = self.history_manager.get_chat_history(
                module_id=module_id,
                profile=profile,
                session_id=effective_session_id,
                return_json=True # Return JSON for API response
            )
            return HistoryResponse(history=history, profile=profile, module_id=module_id)
        except AgentError as e:
             logger.warning(f"Agent error getting history for {module_id}/{profile}: {e}")
             raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
             logger.error(f"Failed getting history for {module_id}/{profile}: {e}", exc_info=True)
             raise HTTPException(status_code=500, detail="Failed to retrieve history.")

    async def _get_status(
        self,
        module_id: str = Path(..., description="Module ID")
    ) -> StatusResponse:
        """Get module status (accesses engine DB directly)."""
        try:
            # Use state service from injected AgentServices
            state = self.services.state_service.get_status(module_id)
            last_updated = self.services.state_service.get_last_updated(module_id)
            return StatusResponse(module_id=module_id, state=state.value, last_updated=last_updated)
        except Exception as e: # Catch potential DB errors or other issues
             logger.error(f"Failed getting status for {module_id}: {e}", exc_info=True)
             raise HTTPException(status_code=500, detail="Failed to retrieve status.")

    async def _stream_chat_history(
        self,
        request: Request, # FastAPI request object needed for SSE
        module_id: str = Path(..., description="Module ID"),
        profile: str = Path(..., description="Profile"),
        session_id: Optional[str] = Query(None, description="Optional session ID")
    ) -> EventSourceResponse:
        """Stream chat history using Server-Sent Events (reads engine DB)."""
        effective_session_id = session_id or str(uuid.UUID(int=0))

        async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
            # Use the history manager instantiated in __init__
            history_manager = self.history_manager
            last_timestamp = datetime.min.replace(tzinfo=UTC) # Timezone-aware min timestamp

            # Send initial state safely
            try:
                initial_history = history_manager.get_chat_history(
                    module_id=module_id, profile=profile,
                    session_id=effective_session_id, return_json=True
                )
                if initial_history:
                    # Get the actual timestamp of the last message in initial history
                    try:
                        # Timestamps should be ISO strings from the DB model/serialization
                        ts_str = initial_history[-1].get('timestamp')
                        if ts_str:
                            # Ensure correct parsing of timezone info if present (Z or +00:00)
                            last_timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).replace(tzinfo=UTC)
                    except (IndexError, ValueError, TypeError) as ts_err:
                         logger.warning(f"Could not parse last timestamp from initial history: {ts_err}")
                         # Keep min timestamp as fallback
                yield {"event": "initial", "data": json.dumps({"history": initial_history})}
            except Exception as e:
                 logger.error(f"SSE initial history error for {module_id}/{profile}: {e}", exc_info=True)
                 yield {"event": "error", "data": json.dumps({"error": "Failed to get initial history"})}
                 return # Stop generator if initial state fails

            # Polling loop
            try:
                while not await request.is_disconnected():
                    new_messages_yielded = False
                    try:
                        with SessionLocal() as db: # Use local session for polling efficiency
                            stmt = (
                                select(ChatHistory)
                                .where(
                                    ChatHistory.module_id == module_id,
                                    ChatHistory.profile == profile,
                                    ChatHistory.session_id == effective_session_id,
                                    ChatHistory.timestamp > last_timestamp # Query for newer messages
                                )
                                .order_by(ChatHistory.timestamp.asc()) # Get in correct order
                            )
                            new_messages = db.execute(stmt).scalars().all()

                            if new_messages:
                                for msg in new_messages:
                                    formatted_message = history_manager._format_message(msg, return_json=True)
                                    yield {"event": "message", "data": json.dumps({"message": formatted_message})}
                                    new_messages_yielded = True
                                # Update last timestamp *after* processing all new messages
                                last_timestamp = new_messages[-1].timestamp
                    except Exception as db_err:
                        logger.error(f"SSE DB poll error for {module_id}/{profile}: {db_err}", exc_info=True)
                        yield {"event": "error", "data": json.dumps({"error": "Database poll failed"})}
                        await asyncio.sleep(5) # Wait longer after DB error
                        continue # Try polling again

                    # Send heartbeat only if no new messages were found in this poll cycle
                    if not new_messages_yielded:
                         yield {"event": "heartbeat", "data": json.dumps({"timestamp": datetime.now(UTC).isoformat()})}

                    await asyncio.sleep(1.5) # Polling interval (adjust as needed)

            except asyncio.CancelledError:
                 logger.info(f"SSE client disconnected for {module_id}/{profile}/{effective_session_id}.")
            except Exception as e:
                logger.error(f"Error in SSE event generator for {module_id}/{profile}: {e}", exc_info=True)
                # Try to yield error if possible
                try: yield {"event": "error", "data": json.dumps({"error": "Streaming error occurred"})}
                except Exception: pass # Ignore if yield fails on disconnect

        # Return the SSE response using the generator
        return EventSourceResponse(event_generator(), ping=15) # Send ping every 15 seconds




    async def _get_profile_tools(
        self,
        module_id: str = Path(..., description="Module ID"),
        profile: str = Path(..., description="Profile")
    ) -> JSONResponse:
        """
        Get the tools available in a specific profile.
        
        Args:
            module_id: The module ID
            profile: The profile name to get tools for
            
        Returns:
            JSONResponse with the list of tools, their descriptions, and parameter schemas
        """
        try:
            logger.info(f"Getting tools for profile '{profile}' of module '{module_id}'")
            
            # Use the agent_runner_service to get the tools schema
            tools_schema = self.agent_runner_service.get_agent_tools_schema(
                module_id=module_id,
                profile=profile
            )
            
            # Return the tools schema
            return JSONResponse(
                content={
                    "status": "success",
                    "profile": profile,
                    "module_id": module_id,
                    "tools": tools_schema
                }
            )
        
        except AgentRunnerError as e:
            logger.error(f"Error getting tools for profile '{profile}': {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error getting tools for profile '{profile}': {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"Internal server error: {str(e)}"
                }
            )
        
        
    def _setup_routes(self):
        """Setup API routes"""
        self.router.add_api_route(
            "/{module_id}/execute", # POST /chat/{module_id}/execute
            self._execute_profile,
            methods=["POST"],
            response_model=ProfileResponse,
            summary="Execute a module profile",
            description="Runs the agent's process_request for the specified profile in a container."
        )
        self.router.add_api_route(
            "/{module_id}/profile/{profile}/history", # GET /chat/{module_id}/profile/{profile}/history
            self._get_profile_history,
            methods=["GET"],
            response_model=HistoryResponse,
            summary="Get chat history for a profile session",
            description="Retrieves the conversation history from the engine's database."
        )
        self.router.add_api_route(
            "/{module_id}/status", # GET /chat/{module_id}/status
            self._get_status,
            methods=["GET"],
            response_model=StatusResponse,
            summary="Get module execution status",
            description="Retrieves the current state (e.g., STANDBY, EXECUTING) from the engine."
        )
        self.router.add_api_route(
            "/{module_id}/profile/{profile}/stream", # GET /chat/{module_id}/profile/{profile}/stream
            self._stream_chat_history,
            methods=["GET"],
            summary="Stream chat history updates",
            description="Establishes an SSE connection to receive chat history updates in real-time."
            # No response_model needed, response_class is EventSourceResponse
        )

        self.router.add_api_route(
            "/{module_id}/profile/{profile}/tool/{tool_name}", # POST /chat/{module_id}/profile/{profile}/tool/{tool_name}
            self._execute_profile_tool,
            methods=["POST"],
            summary="Execute a specific tool/action from a profile",
            description="Directly execute a tool/action from an agent profile with provided parameters."
        )
        self.router.add_api_route(
            "/{module_id}/profile/{profile}/tools", # GET /chat/{module_id}/profile/{profile}/tools
            self._get_profile_tools,
            methods=["GET"],
            summary="Get tools available in a profile",
            description="Returns a list of tools with their descriptions and parameter schemas for a specific profile."
        )
