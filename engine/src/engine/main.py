import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.apis.action import ActionRouter
from engine.apis.agent import AgentRouter

# Import routers
from engine.apis.kit import KitRouter

# Import utilities
from engine.apis.model import ModelRouter
from engine.apis.module import ModuleRouter
from engine.apis.project import ProjectRouter
from engine.apis.repository import RepositoryRouter
from engine.apis.resource import ResourceRouter  # New import
from engine.apis.workflow import WorkflowRouter
from engine.services.execution.action import ActionService

# Import new service and router
from engine.services.execution.agent import AgentService

# Import services
from engine.services.core.kit import KitService
from engine.services.execution.model import ModelService
from engine.services.core.module import ModuleService
from engine.services.core.project import ProjectService
from engine.services.storage.repository import RepoService
from engine.services.storage.resource import ResourceService  # New import
from engine.services.execution.stage_state import StageStateService  # Add this import
from engine.services.execution.workflow import WorkflowService

load_dotenv()

os.environ["ANTHROPIC_API_KEY"] = "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"


# Create FastAPI app
app = FastAPI(title="Repository and Module Management API")

# Configuration
BASE_DATA_DIR = Path(".data")
REPO_BASE_DIR = BASE_DATA_DIR / "repositories"
SEARCH_INDEX_DIR = BASE_DATA_DIR / "search_indices"
KIT_BASE_DIR = BASE_DATA_DIR / "kit"


# Create necessary directories
BASE_DATA_DIR.mkdir(exist_ok=True)
REPO_BASE_DIR.mkdir(exist_ok=True)
SEARCH_INDEX_DIR.mkdir(exist_ok=True)
KIT_BASE_DIR.mkdir(exist_ok=True)

# Initialize services
repo_service = RepoService(
    base_path=REPO_BASE_DIR,
    search_index_path=SEARCH_INDEX_DIR
)

kit_service = KitService(base_path=KIT_BASE_DIR)

project_service = ProjectService()



# Add after other service initializations
stage_state_service = StageStateService()

module_service = ModuleService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    repo_service=repo_service,
    stage_state_service=stage_state_service  # Add this
)


resource_service = ResourceService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    repo_base=str(REPO_BASE_DIR),  # Add repo base directory
    module_service=module_service
)
model_service = ModelService()


action_service = ActionService(repo_service=repo_service)

# Add this with other service initializations
workflow_service = WorkflowService(
    workspace_base=str(KIT_BASE_DIR),
    module_base=str(KIT_BASE_DIR),
    module_service=module_service,
    action_service=action_service,
    resource_service=resource_service,
    repo_service=repo_service,
)






# Initialize Agent service
agent_service = AgentService(
    workflow_service=workflow_service,
    model_service=model_service,
    stage_state_service=stage_state_service,
    repo_service=repo_service,
    module_service=module_service,
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

# Initialize AI workflow router
agent_router = AgentRouter(
    agent_service=agent_service,
    prefix="/agent"
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
app.include_router(agent_router.router)





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
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
