import os
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict
import secrets
from base64 import b64decode

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from engine.apis.action import ActionRouter
# from engine.apis.agent import AgentRouter

# Import routers
from engine.apis.chat import ChatRouter
from engine.apis.kit import KitRouter

# Import utilities
from engine.apis.model import ModelRouter
from engine.apis.module import ModuleRouter
from engine.apis.project import ProjectRouter
from engine.apis.repository import RepositoryRouter
from engine.apis.resource import ResourceRouter
from engine.apis.workflow import WorkflowRouter
from engine.services.agents.base_agent import AgentServices
from engine.services.execution.action import ActionService

# Import services
from engine.services.core.kit import KitService
from engine.services.execution.model import ModelService
from engine.services.core.module import ModuleService
from engine.services.core.project import ProjectService
from engine.services.storage.repository import RepoService
from engine.services.storage.resource import ResourceService
from engine.services.execution.state import StateService
from engine.services.execution.workflow import WorkflowService
from engine.services.storage.vector_store import VectorStoreService
from engine.services.storage.embedder import EmbeddingService
from engine.apis.models.embedding import EmbeddingRouter



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


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("ADMIN_USERNAME")
    correct_password = os.getenv("ADMIN_PASSWORD")
    
    if not secrets.compare_digest(credentials.username, correct_username) or \
       not secrets.compare_digest(credentials.password, correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Create FastAPI app with exception handlers
app = FastAPI(
    title="Repository and Module Management API",
    debug=True,  # Enable debug mode for detailed error responses
    dependencies=[Depends(get_current_user)]  # Apply basic auth to all routes
)
app.add_middleware(LogMiddleware)

# Configuration
BASE_DATA_DIR = Path(os.getenv("DATA_DIR"))
REPO_BASE_DIR = BASE_DATA_DIR / "repositories"
KIT_BASE_DIR = BASE_DATA_DIR / "kit"

# Create necessary directories
BASE_DATA_DIR.mkdir(exist_ok=True)
REPO_BASE_DIR.mkdir(exist_ok=True)
KIT_BASE_DIR.mkdir(exist_ok=True)

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
    stage_state_service=state_service,
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
workflow_service = WorkflowService(
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
    prefix="/kit"
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
workflow_router = WorkflowRouter(
    workflow_service=workflow_service,
    prefix="/workflow"
)

# 3. Add to router initializations after other routers
embedding_router = EmbeddingRouter(
    embedding_service=embedding_service,
    prefix="/embedding"
)

# Include routers
app.include_router(kit_router.router)
app.include_router(module_router.router)
app.include_router(repo_router.router)
app.include_router(project_router.router)
app.include_router(resource_router.router)  # Add resource router
app.include_router(model_router.router)
app.include_router(operation_router.router)
app.include_router(workflow_router.router)
app.include_router(embedding_router.router)


agent_services = AgentServices(
    model_service=model_service,
    workflow_service=workflow_service,
    state_service=state_service,
    module_service=module_service,
    repo_service=repo_service
)

chat_router = ChatRouter(
    agent_services=agent_services
)

# Include the router
app.include_router(chat_router.router)

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
    """Initialize database on startup"""
    pass

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        access_log=True,
        reload=True
    )

    server = uvicorn.Server(uvicorn_config)
    server.run()
