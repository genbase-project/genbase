import asyncio
import os
import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List
import secrets
from base64 import b64decode
from rpyc import ThreadedServer
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from loguru import logger
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware


# Import routers
from engine.apis.authz import AuthzRouter
from engine.apis.chat import ChatRouter
from engine.apis.kit import KitRouter

# Import utilities
from engine.apis.model import ModelRouter
from engine.apis.module import ModuleRouter
from engine.apis.project import ProjectRouter
from engine.apis.repository import WorkspaceRouter
from engine.apis.resource import ResourceRouter
from engine.apis.profile import ProfileRouter
from engine.auth.schemas import UserCreate, UserRead, UserUpdate
from engine.auth.superuser import create_default_superuser
from engine.const import BASE_DATA_DIR, KIT_BASE_DIR, REPO_BASE_DIR, RPC_PORT
from engine.db.models import User
from engine.db.session import SessionLocal
from engine.services.agents.types import AgentServices
from engine.services.core.api_key import ApiKeyService
from engine.services.execution.agent_execution import AgentRunnerService


# Import services
from engine.services.core.kit import KitService
from engine.services.execution.model import ModelService
from engine.services.core.module import ModuleService
from engine.services.core.project import ProjectService
from engine.services.platform_rpyc_service import PlatformRPyCService
from engine.services.storage.repository import WorkspaceService
from engine.services.storage.resource import ResourceService
from engine.services.execution.state import StateService
from engine.services.execution.profile import ProfileService

from engine.services.storage.embedder import EmbeddingService
from engine.apis.embedding import EmbeddingRouter

from engine.apis.gateway import LLMGatewayRouter
from engine.auth.users import auth_backend, current_active_user, fastapi_users


load_dotenv()



# Basic auth configuration
security = HTTPBasic()

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            logger.info(f"{request.method} {request.url.path}")
            
            # Try to log request body for debugging if needed
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if os.environ.get("DEV_MODE"):
                        logger.debug(f"Request body: {body.decode()}")
                except:
                    pass
                    
            response = await call_next(request)
            
            process_time = time.time() - start_time
            logger.info(f"Completed {request.method} {request.url.path} in {process_time:.2f}s")
            
            return response
            
        except Exception as e:
            # Enhanced error logging
            logger.error(f"""
REQUEST FAILED!
URL: {request.url.path}
Method: {request.method}
Error: {str(e)}
Stack Trace:
{traceback.format_exc()}
            """)
            
            # Return error response with stack trace in development
            if os.getenv("DEBUG"):
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": str(e),
                        "stack_trace": traceback.format_exc().split('\n')
                    }
                )
            raise












# Create FastAPI app with exception handlers
app = FastAPI(
    title="Genbase API",
    debug=True,  # Enable debug mode for detailed error responses
    root_path="/api/v1"  
)
app.add_middleware(LogMiddleware)




@app.get("/users", response_model=List[UserRead], tags=["users"], dependencies=[Depends(current_active_user)])
async def list_users(
    user: User = Depends(current_active_user)
):
    with SessionLocal() as session:


        stmt = select(User)
        result = session.execute(stmt)
        all_users = result.scalars().all()

        return all_users



### Authentication Dependency ###
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
        dependencies=[Depends(fastapi_users.current_user(active=True, superuser=True))]
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
















































# Create necessary directories
BASE_DATA_DIR.mkdir(exist_ok=True)
REPO_BASE_DIR.mkdir(exist_ok=True)
KIT_BASE_DIR.mkdir(exist_ok=True)



api_key_service = ApiKeyService()
# Initialize services
repo_service = WorkspaceService(
    base_path=REPO_BASE_DIR
)

kit_service = KitService(base_path=KIT_BASE_DIR)

project_service = ProjectService()

# Add after other service initializations
state_service = StateService()

module_service = ModuleService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    repo_service=repo_service,
    state_service=state_service,
    kit_service=kit_service
)

model_service = ModelService()
embedding_service = EmbeddingService()

resource_service = ResourceService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    repo_base=str(REPO_BASE_DIR),  # Add repo base directory
    module_service=module_service,
    model_service=model_service
)


# Add this with other service initializations
profile_service = ProfileService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    module_service=module_service,
    resource_service=resource_service,
    repo_service=repo_service,
    kit_service=kit_service
)


# Initialize routers
authz_router = AuthzRouter()


kit_router = KitRouter(
   kit_service=kit_service,
    prefix="/kit",
    
)

repo_router = WorkspaceRouter(
    repo_service=repo_service,
    prefix="/repository"
)

project_router = ProjectRouter(
    project_service=project_service,
    prefix="/project"
)

module_router = ModuleRouter(
    module_service=module_service,
    api_key_service=api_key_service,
    prefix="/module"
)

# Initialize resource router
resource_router = ResourceRouter(
    resource_service=resource_service,
    prefix="/resource"
)

# Initialize router
model_router = ModelRouter(model_service)


# Add this with other router initializations
profile_router = ProfileRouter(
    profile_service=profile_service,
    prefix="/profile"
)

# 3. Add to router initializations after other routers
embedding_router = EmbeddingRouter(
    embedding_service=embedding_service,
    prefix="/embedding"
)



# Initialize LLM gateway router
llm_gateway_router = LLMGatewayRouter(
    model_service=model_service,
    api_key_service=api_key_service
)




# Include routers
app.include_router(kit_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(module_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(repo_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(project_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(resource_router.router,     dependencies=[Depends(current_active_user)])  # Add resource router
app.include_router(model_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(profile_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(embedding_router.router,     dependencies=[Depends(current_active_user)])

app.include_router(authz_router.router,      dependencies=[Depends(current_active_user)])



gateway_app = FastAPI()
gateway_app.include_router(llm_gateway_router.router)

# Mount the gateway app to the main app
app.mount("/gateway", gateway_app)


agent_runner_service = AgentRunnerService(
    repo_service=repo_service,
    module_service=module_service,
    kit_service=kit_service,
    state_service=state_service,
)

agent_services = AgentServices(
    model_service=model_service,
    profile_service=profile_service,
    state_service=state_service,
    module_service=module_service,
    repo_service=repo_service,
    agent_runner_service=agent_runner_service,
)

chat_router = ChatRouter(
    agent_services=agent_services,
    agent_runner_service=agent_runner_service
)


# Include the router
app.include_router(chat_router.router,    
                   dependencies=[Depends(current_active_user)]
                   )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





















platform_rpyc_service_instance = PlatformRPyCService(services=agent_services)

# Global variable for the RPyC server thread
rpyc_server_thread = None
rpyc_server_instance = None

def start_rpyc_server():
    global rpyc_server_instance
    # Get host and port from environment variables
    rpyc_host = os.getenv("RPYC_HOST", "0.0.0.0") # Listen on all interfaces
    rpyc_port = RPC_PORT # Default RPyC port

    logger.info(f"Attempting to start RPyC ThreadedServer on {rpyc_host}:{rpyc_port}")

    try:
        rpyc_server_instance = ThreadedServer(
            platform_rpyc_service_instance,
            hostname=rpyc_host,
            port=rpyc_port,
            
            protocol_config={
                'allow_public_attrs': False, # More secure default
                'allow_pickle': True,       # Avoid pickle
                'sync_request_timeout': 300, # Timeout for requests
            }
        )
        # Start blocks until the server is shut down
        rpyc_server_instance.start()

    except OSError as e:
        logger.error(f"Failed to start RPyC server on {rpyc_host}:{rpyc_port}. Port likely in use. Error: {e}")
    except Exception as e:
        logger.error(f"Critical error starting RPyC server: {e}", exc_info=True)
    finally:
        logger.info("RPyC server thread finished.")





# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup and run migrations"""
    try:
        global rpyc_server_thread
        logger.info("Running database migrations...")
        
        # Use subprocess to run alembic migrations
        import subprocess
        import sys
        
        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=False
        )
        await create_default_superuser()

        
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.error(f"Migration failed with code {result.returncode}")
            logger.error(f"Migration error: {result.stderr}")
            logger.error(f"Migration output: {result.stdout}")
            
            sys.exit(1)





        # Start RPyC server in a background thread
        logger.info("Starting RPyC server thread...")
        rpyc_server_thread = threading.Thread(target=start_rpyc_server, daemon=True)
        rpyc_server_thread.start()
        # Give it a moment to start up - check logs for confirmation/errors
        await asyncio.sleep(1) # Small delay to check logs if needed
        if rpyc_server_thread.is_alive():
            logger.info("RPyC server thread appears to be running.")
        else:
            logger.error("RPyC server thread failed to start or exited immediately. Check logs.")


    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        access_log=True,
        reload=True,
        reload_dirs=["src"]
    )

    server = uvicorn.Server(uvicorn_config)
    server.run()
