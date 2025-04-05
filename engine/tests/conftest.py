import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager

# SQLAlchemy testing imports
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import your Base
from engine.db.models import Base

# Enable PDM pytest plugins
pytest_plugins = ["pdm.pytest"]

# --- Mock Fixtures ---

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path



@pytest.fixture
def engine_project(project):
    project.pyproject.settings["project"] = {
        "name": "engine",
        "version": "0.1.0",
        "dependencies": [],
    }
    return project

# --- Database Fixtures ---

@pytest.fixture(scope='module')
def engine() -> Engine:
    """Generate the Engine. Use an in-memory DB."""
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables from the models
    Base.metadata.create_all(engine)
    
    # Print the tables for debugging
    inspector = inspect(engine)
    print(f"Tables created: {inspector.get_table_names()}")
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(engine)

@pytest.fixture(scope='module')
def connection(engine: Engine):
    """Generate a connection to the DB."""
    connection = engine.connect()
    yield connection
    connection.close()

@pytest.fixture
def db_session(connection: Connection):
    """For every test generate a new session with transaction rollback."""
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()

@pytest.fixture
def mock_db_context(db_session):
    """
    Creates a real context manager that yields the db_session.
    This fixes the 'function does not support context manager protocol' error.
    """
    @contextmanager
    def session_context_manager():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise
    
    return session_context_manager