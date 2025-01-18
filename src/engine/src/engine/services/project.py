from dataclasses import dataclass
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

@dataclass
class ProjectMetadata:
    """Project metadata"""
    id: str
    name: str
    created_at: str

class ProjectError(Exception):
    """Base exception for project errors"""
    pass

class ProjectService:
    """Service for managing projects"""
    
    def __init__(self, db_path: str):
        """
        Initialize project service
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()
        self._ensure_default_project()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)
    
    def _ensure_default_project(self):
        """Ensure default project exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if default project exists
                cursor = conn.execute(
                    "SELECT id FROM projects WHERE name = ?",
                    ("default",)
                )
                if not cursor.fetchone():
                    # Create default project
                    default_id = "00000000-0000-0000-0000-000000000000"
                    created_at = datetime.utcnow().isoformat()
                    conn.execute(
                        """
                        INSERT INTO projects (id, name, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (default_id, "default", created_at)
                    )
        except Exception as e:
            raise ProjectError(f"Failed to ensure default project: {str(e)}")
    
    def create_project(self, name: str) -> ProjectMetadata:
        """Create new project"""
        try:
            project_id = str(uuid.uuid4())
            created_at = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO projects (id, name, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (project_id, name, created_at)
                )
            
            return ProjectMetadata(
                id=project_id,
                name=name,
                created_at=created_at
            )
        except sqlite3.IntegrityError:
            raise ProjectError(f"Project with name '{name}' already exists")
        except Exception as e:
            raise ProjectError(f"Failed to create project: {str(e)}")
    
    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Get project by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, name, created_at FROM projects WHERE id = ?",
                    (project_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return ProjectMetadata(
                        id=result[0],
                        name=result[1],
                        created_at=result[2]
                    )
                return None
                
        except Exception as e:
            raise ProjectError(f"Failed to get project: {str(e)}")
    
    def get_all_projects(self) -> List[ProjectMetadata]:
        """Get all projects"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, name, created_at FROM projects"
                )
                return [
                    ProjectMetadata(
                        id=row[0],
                        name=row[1],
                        created_at=row[2]
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            raise ProjectError(f"Failed to get projects: {str(e)}")
    