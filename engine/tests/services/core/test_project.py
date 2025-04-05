# tests/services/core/test_project.py

import pytest
from datetime import datetime, UTC
from contextlib import contextmanager # Import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from engine.services.core.project import ProjectService, ProjectMetadata, ProjectError
from engine.db.models import Project

# --- Test Fixtures ---

@pytest.fixture
def project_service(db_session: Session) -> ProjectService: # Use db_session directly
    """Fixture providing a ProjectService instance patched with the test DB context."""
    service = ProjectService()

    # Define the function that returns the context manager yielding the db_session
    def get_test_db():
        @contextmanager
        def test_db_context():
            try:
                yield db_session
            finally:
                # No specific cleanup needed here as db_session handles rollback/close
                pass
        # Return the actual context manager instance
        return test_db_context()

    # Directly assign the function (which returns the context manager)
    # to the service's internal method
    service._get_db = get_test_db
    yield service # yield the patched service

@pytest.fixture
def create_test_project(db_session: Session) -> Project:
    """Fixture to create a standard test project in the DB."""
    project = Project(
        id=str(uuid.uuid4()),
        name="test-project-1",
        created_at=datetime.now(UTC)
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project

# --- Test Cases ---

class TestProjectService:

    def test_ensure_default_project_creation(self, db_session: Session): # Use db_session
        """Test that the default project is created if it doesn't exist."""
        existing_default = db_session.get(Project, "00000000-0000-0000-0000-000000000000")
        if existing_default:
            db_session.delete(existing_default)
            db_session.commit()

        # Create a temporary service instance *for this test* to trigger init
        temp_service = ProjectService()
        # Patch its _get_db for the duration of the init call in this test
        def get_temp_test_db():
            @contextmanager
            def temp_test_db_context():
                yield db_session
            return temp_test_db_context()
        temp_service._get_db = get_temp_test_db
        temp_service._ensure_default_project() # Call the method directly

        # Verify default project now exists in the DB
        default_project = db_session.get(Project, "00000000-0000-0000-0000-000000000000")
        assert default_project is not None
        assert default_project.name == "default"
        assert default_project.id == "00000000-0000-0000-0000-000000000000"

    def test_ensure_default_project_already_exists(self, db_session: Session): # Use db_session
        """Test that initializing the service doesn't fail if default project exists."""
        default_id = "00000000-0000-0000-0000-000000000000"
        if not db_session.get(Project, default_id):
            default_project = Project(id=default_id, name="default", created_at=datetime.now(UTC))
            db_session.add(default_project)
            db_session.commit()

        # Initialize service - should not raise an error
        try:
            temp_service = ProjectService()
            def get_temp_test_db():
                @contextmanager
                def temp_test_db_context():
                    yield db_session
                return temp_test_db_context()
            temp_service._get_db = get_temp_test_db
            temp_service._ensure_default_project()
        except Exception as e:
            pytest.fail(f"_ensure_default_project raised an exception unexpectedly: {e}")

        assert db_session.get(Project, default_id) is not None


    def test_create_project_success(self, project_service: ProjectService, db_session: Session):
        project_name = "new-project-success"
        result = project_service.create_project(project_name)

        assert isinstance(result, ProjectMetadata)
        assert result.name == project_name
        assert isinstance(uuid.UUID(result.id), uuid.UUID)

        db_project = db_session.get(Project, result.id)
        assert db_project is not None
        assert db_project.name == project_name

    def test_create_project_duplicate_name(self, project_service: ProjectService, create_test_project: Project):
        duplicate_name = create_test_project.name
        with pytest.raises(ProjectError, match=f"Project with name '{duplicate_name}' already exists"):
            project_service.create_project(duplicate_name)

    def test_get_project_success(self, project_service: ProjectService, create_test_project: Project):
        result = project_service.get_project(create_test_project.id)

        assert isinstance(result, ProjectMetadata)
        assert result.id == create_test_project.id
        assert result.name == create_test_project.name
        assert result.created_at == create_test_project.created_at.isoformat()

    def test_get_project_not_found(self, project_service: ProjectService):
        non_existent_id = str(uuid.uuid4())
        result = project_service.get_project(non_existent_id)
        assert result is None

    def test_get_all_projects(self, project_service: ProjectService, db_session: Session, create_test_project: Project):
        # Ensure default project exists for this test run
        default_id = "00000000-0000-0000-0000-000000000000"
        if not db_session.get(Project, default_id):
             default_project = Project(id=default_id, name="default", created_at=datetime.now(UTC))
             db_session.add(default_project)
             db_session.commit()

        # Create another project for testing multiple retrieval
        project2 = Project(id=str(uuid.uuid4()), name="another-test-project", created_at=datetime.now(UTC))
        db_session.add(project2)
        db_session.commit()

        results = project_service.get_all_projects()

        assert isinstance(results, list)
        project_ids = {p.id for p in results}
        assert len(project_ids) >= 3 # Default, create_test_project, project2
        assert default_id in project_ids
        assert create_test_project.id in project_ids
        assert project2.id in project_ids
        assert all(isinstance(p, ProjectMetadata) for p in results)

    def test_get_all_projects_includes_default(self, project_service: ProjectService, db_session: Session):
        default_id = "00000000-0000-0000-0000-000000000000"
        if not db_session.get(Project, default_id):
            default_project = Project(id=default_id, name="default", created_at=datetime.now(UTC))
            db_session.add(default_project)
            db_session.commit()

        results = project_service.get_all_projects()
        assert any(p.id == default_id for p in results)

    def test_project_metadata_from_orm(self):
        created_time = datetime.now(UTC)
        project_orm = Project(
            id="orm-test-id",
            name="orm-test-name",
            created_at=created_time
        )
        metadata = ProjectMetadata.from_orm(project_orm)

        assert metadata.id == "orm-test-id"
        assert metadata.name == "orm-test-name"
        assert metadata.created_at == created_time.isoformat()