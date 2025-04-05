import os
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List
import secrets
from base64 import b64decode

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from loguru import logger
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from engine.apis.action import ActionRouter

# Import routers
from engine.apis.chat import ChatRouter
from engine.apis.kit import KitRouter

# Import utilities
from engine.apis.model import ModelRouter
from engine.apis.module import ModuleRouter
from engine.apis.project import ProjectRouter
from engine.apis.repository import RepositoryRouter
from engine.apis.resource import ResourceRouter
from engine.apis.profile import ProfileRouter
from engine.auth.schemas import UserCreate, UserRead, UserUpdate
from engine.auth.superuser import create_default_superuser
from engine.const import BASE_DATA_DIR, KIT_BASE_DIR, REPO_BASE_DIR
from engine.db.models import User
from engine.db.session import SessionLocal
from engine.services.agents.base_agent import AgentServices
from engine.services.core.api_key import ApiKeyService
from engine.services.execution.action import ActionService

# Import services
from engine.services.core.kit import KitService
from engine.services.execution.model import ModelService
from engine.services.core.module import ModuleService
from engine.services.core.project import ProjectService
from engine.services.storage.repository import RepoService
from engine.services.storage.resource import ResourceService
from engine.services.execution.state import StateService
from engine.services.execution.profile import ProfileService
from engine.services.storage.vector_store import VectorStoreService
from engine.services.storage.embedder import EmbeddingService
from engine.apis.embedding import EmbeddingRouter

from engine.apis.llm_gateway import LLMGatewayRouter
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
repo_service = RepoService(
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

action_service = ActionService(repo_service=repo_service)

# Add this with other service initializations
profile_service = ProfileService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    module_service=module_service,
    action_service=action_service,
    resource_service=resource_service,
    repo_service=repo_service,
    kit_service=kit_service
)

# Initialize routers
kit_router = KitRouter(
   kit_service=kit_service,
    prefix="/kit",
    
)

repo_router = RepositoryRouter(
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

# Add to router initialization
operation_router = ActionRouter(
    action_service=action_service,
    prefix="/action"
)

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
app.include_router(operation_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(profile_router.router,     dependencies=[Depends(current_active_user)])
app.include_router(embedding_router.router,     dependencies=[Depends(current_active_user)])




gateway_app = FastAPI()
gateway_app.include_router(llm_gateway_router.router)

# Mount the gateway app to the main app
app.mount("/gateway", gateway_app)


agent_services = AgentServices(
    model_service=model_service,
    profile_service=profile_service,
    state_service=state_service,
    module_service=module_service,
    repo_service=repo_service
)

chat_router = ChatRouter(
    agent_services=agent_services
)

# Include the router
app.include_router(chat_router.router,    dependencies=[Depends(current_active_user)])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup and run migrations"""
    try:
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
