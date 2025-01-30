import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch
from sqlalchemy.exc import IntegrityError

from engine.services.core.project import ProjectService, ProjectMetadata, ProjectError
from engine.db.models import Project

@pytest.fixture
def mock_db_session():
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    return session

@pytest.fixture
def project_service():
    with patch('engine.services.core.project.SessionLocal') as mock_session:
        service = ProjectService()
        yield service

@pytest.fixture
def mock_project():
    return Project(
        id="test-id",
        name="test-project",
        created_at=datetime.now(UTC)
    )

class TestProjectService:
    def test_ensure_default_project_exists(self, mock_db_session):
        """Test default project creation when it doesn't exist"""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            ProjectService()
            
            # Verify default project was created
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            
            # Verify correct default project data
            project = mock_db_session.add.call_args[0][0]
            assert project.id == "00000000-0000-0000-0000-000000000000"
            assert project.name == "default"

    def test_ensure_default_project_already_exists(self, mock_db_session):
        """Test default project is not created when it already exists"""
        default_project = Project(
            id="00000000-0000-0000-0000-000000000000",
            name="default",
            created_at=datetime.now(UTC)
        )
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = default_project
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            ProjectService()
            mock_db_session.add.assert_not_called()
            mock_db_session.commit.assert_not_called()

    def test_create_project(self, project_service, mock_db_session, mock_project):
        """Test successful project creation"""
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            with patch('uuid.uuid4', return_value=mock_project.id):
                result = project_service.create_project("test-project")
                
                assert isinstance(result, ProjectMetadata)
                assert result.name == "test-project"
                assert result.id == mock_project.id
                
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()

    def test_create_project_duplicate_name(self, project_service, mock_db_session):
        """Test project creation with duplicate name"""
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock(side_effect=IntegrityError(None, None, None))
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            with pytest.raises(ProjectError, match="Project with name 'test-project' already exists"):
                project_service.create_project("test-project")

    def test_get_project(self, project_service, mock_db_session, mock_project):
        """Test getting project by ID"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            result = project_service.get_project(mock_project.id)
            
            assert isinstance(result, ProjectMetadata)
            assert result.id == mock_project.id
            assert result.name == mock_project.name

    def test_get_project_not_found(self, project_service, mock_db_session):
        """Test getting non-existent project"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            result = project_service.get_project("non-existent-id")
            assert result is None

    def test_get_all_projects(self, project_service, mock_db_session, mock_project):
        """Test getting all projects"""
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_project]
        
        with patch('engine.services.core.project.SessionLocal', return_value=mock_db_session):
            results = project_service.get_all_projects()
            
            assert isinstance(results, list)
            assert len(results) == 1
            assert all(isinstance(r, ProjectMetadata) for r in results)
            assert results[0].id == mock_project.id
            assert results[0].name == mock_project.name



    def test_project_metadata_from_orm(self, mock_project):
        """Test ProjectMetadata.from_orm conversion"""
        metadata = ProjectMetadata.from_orm(mock_project)
        
        assert isinstance(metadata, ProjectMetadata)
        assert metadata.id == mock_project.id
        assert metadata.name == mock_project.name
        assert metadata.created_at == mock_project.created_at.isoformat()
