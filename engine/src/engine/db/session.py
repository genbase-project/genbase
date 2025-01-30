from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import URL


# Create engine
engine = create_engine(
    "postgresql://neondb_owner:npg_a3GpUdvXS0WO@ep-lucky-field-a19xu8ps-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
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