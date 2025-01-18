import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Import services
from engine.services.module import ModuleService
from engine.services.repository import RepoService
from engine.services.runtime_module import RuntimeModuleService
from engine.services.project import ProjectService
from engine.services.resource import ResourceService  # New import

# Import routers
from engine.apis.module import ModuleRouter
from engine.apis.repository import RepositoryRouter
from engine.apis.runtime_module import RuntimeModuleRouter
from engine.apis.project import ProjectRouter
from engine.apis.resource import ResourceRouter  # New import

# Import utilities
from engine.apis.model import ModelRouter
from engine.services.model import ModelService
from engine.apis.operation import OperationRouter
from engine.services.operation import OperationService
from engine.utils.file import extract_zip, is_safe_path
from engine.utils.git import create_search_index

from dotenv import load_dotenv

load_dotenv()

os.environ["ANTHROPIC_API_KEY"] = "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"


# Create FastAPI app
app = FastAPI(title="Repository and Module Management API")

# Configuration
BASE_DATA_DIR = Path(".data")
REPO_BASE_DIR = BASE_DATA_DIR / "repositories"
SEARCH_INDEX_DIR = BASE_DATA_DIR / "search_indices"
PACKAGE_BASE_DIR = BASE_DATA_DIR / "modules"
DB_PATH = BASE_DATA_DIR / "runtime.db"

# Create necessary directories
BASE_DATA_DIR.mkdir(exist_ok=True)
REPO_BASE_DIR.mkdir(exist_ok=True)
SEARCH_INDEX_DIR.mkdir(exist_ok=True)
PACKAGE_BASE_DIR.mkdir(exist_ok=True)

# Initialize services
repo_service = RepoService(
    base_path=REPO_BASE_DIR,
    search_index_path=SEARCH_INDEX_DIR,
    create_index_func=create_search_index
)

module_service = ModuleService(base_path=PACKAGE_BASE_DIR)

project_service = ProjectService(
    db_path=str(DB_PATH)
)

runtime_service = RuntimeModuleService(
    db_path=str(DB_PATH),
    workspace_base=str(PACKAGE_BASE_DIR),
    repo_service=repo_service
)

resource_service = ResourceService(
    workspace_base=str(PACKAGE_BASE_DIR),
    module_base=str(PACKAGE_BASE_DIR),
    repo_base=str(REPO_BASE_DIR),  # Add repo base directory
    runtime_service=runtime_service
)
model_service = ModelService()


operation_service = OperationService()




# Initialize routers
module_router = ModuleRouter(
    module_service=module_service,
    prefix="/module"
)

repo_router = RepositoryRouter(
    repo_service=repo_service,
    prefix="/repo"
)

project_router = ProjectRouter(
    project_service=project_service,
    prefix="/project"
)

runtime_router = RuntimeModuleRouter(
    module_service=runtime_service,
    prefix="/runtime"
)

# Initialize resource router
resource_router = ResourceRouter(
    resource_service=resource_service,
    prefix="/resource"
)


# Initialize router
model_router = ModelRouter(model_service)
    

# Add to router initialization
operation_router = OperationRouter(
    operation_service=operation_service,
    prefix="/operation"
)


# Include routers
app.include_router(module_router.router)
app.include_router(repo_router.router)
app.include_router(project_router.router)
app.include_router(runtime_router.router)
app.include_router(resource_router.router)  # Add resource router
app.include_router(model_router.router)
app.include_router(operation_router.router)



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
    project_service._init_db()  # Initialize project tables first
    runtime_service._init_db()  # Then initialize runtime module tables

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
