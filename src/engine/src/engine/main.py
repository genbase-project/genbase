from fastapi import FastAPI
from pathlib import Path
import sqlite3

# Import services
from engine.services.module import ModuleService
from engine.services.repository import RepoService
from engine.services.runtime_module import RuntimeModuleService

# Import routers
from engine.apis.module import ModuleRouter
from engine.apis.repository import RepositoryRouter
from engine.apis.runtime_module import RuntimeModuleRouter

# Import utilities
from engine.utils.file import extract_zip, is_safe_path
from engine.utils.git import create_search_index

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

runtime_service = RuntimeModuleService(
    db_path=str(DB_PATH),
    workspace_base=str(PACKAGE_BASE_DIR),
    repo_service=repo_service  # Pass repo service for git operations
)

# Initialize routers
module_router = ModuleRouter(
    module_service=module_service,
    prefix="/module"
)

repo_router = RepositoryRouter(
    repo_service=repo_service,
    prefix="/repo"
)

runtime_router = RuntimeModuleRouter(
    module_service=runtime_service,
    prefix="/runtime"
)

# Include routers
app.include_router(module_router.router)
app.include_router(repo_router.router)
app.include_router(runtime_router.router)

# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize SQLite database on startup"""
    runtime_service._init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


    