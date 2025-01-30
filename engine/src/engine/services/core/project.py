import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from engine.db.models import Project
from engine.db.session import SessionLocal


@dataclass
class ProjectMetadata:
    """Project metadata"""
    id: str
    name: str
    created_at: str

    @classmethod
    def from_orm(cls, project: Project) -> 'ProjectMetadata':
        """Convert SQLAlchemy Project object to ProjectMetadata"""
        return cls(
            id=project.id,
            name=project.name,
            created_at=project.created_at.isoformat()
        )


class ProjectError(Exception):
    """Base exception for project errors"""
    pass


class ProjectService:
    """Service for managing projects"""

    def __init__(self):
        """Initialize project service"""
        self._ensure_default_project()

    def _get_db(self) -> Session:
        return SessionLocal()

    def _ensure_default_project(self):
        """Ensure default project exists"""
        try:
            with self._get_db() as db:
                # Check if default project exists
                default_project = db.query(Project).filter_by(name="default").first()
                
                if not default_project:
                    # Create default project
                    default_id = "00000000-0000-0000-0000-000000000000"
                    default_project = Project(
                        id=default_id,
                        name="default",
                        created_at=datetime.now(UTC)
                    )
                    db.add(default_project)
                    db.commit()

        except Exception as e:
            raise ProjectError(f"Failed to ensure default project: {str(e)}")

    def create_project(self, name: str) -> ProjectMetadata:
        """Create new project"""
        try:
            project_id = str(uuid.uuid4())
            
            with self._get_db() as db:
                project = Project(
                    id=project_id,
                    name=name,
                    created_at=datetime.now(UTC)
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                
                return ProjectMetadata.from_orm(project)

        except IntegrityError:
            raise ProjectError(f"Project with name '{name}' already exists")
        except Exception as e:
            raise ProjectError(f"Failed to create project: {str(e)}")

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Get project by ID"""
        try:
            with self._get_db() as db:
                stmt = select(Project).where(Project.id == project_id)
                project = db.execute(stmt).scalar_one_or_none()
                
                if project:
                    return ProjectMetadata.from_orm(project)
                return None

        except Exception as e:
            raise ProjectError(f"Failed to get project: {str(e)}")

    def get_all_projects(self) -> List[ProjectMetadata]:
        """Get all projects"""
        try:
            with self._get_db() as db:
                stmt = select(Project)
                projects = db.execute(stmt).scalars().all()
                return [ProjectMetadata.from_orm(project) for project in projects]

        except Exception as e:
            raise ProjectError(f"Failed to get projects: {str(e)}")