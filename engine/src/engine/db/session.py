from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
load_dotenv()

# Create engine
engine = create_engine(
    os.environ.get("DATABASE_URL"),
    pool_pre_ping=True,  # Enables connection health checks
    pool_size=5,         # Default pool size
    max_overflow=10      # Allow up to 10 connections beyond pool_size
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()