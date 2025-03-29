from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from typing import Union, Type

from engine.db.models import User

load_dotenv()

def prepare_async_db_url(url):
    """Convert a PostgreSQL URL to an AsyncPG compatible URL"""
    if not url or not url.startswith("postgresql://"):
        return url
        
    # Parse the URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove SSL mode parameters that asyncpg doesn't support
    query_params.pop("sslmode", None)
    
    # Create a new query string
    new_query = urlencode(query_params, doseq=True)
    
    # Reconstruct the URL with asyncpg driver and without sslmode
    new_url = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
    if new_query:
        new_url += f"?{new_query}"
    
    return new_url

# Get database URLs for both sync and async connections
SYNC_DATABASE_URL = os.environ.get("DATABASE_URL")
ASYNC_DATABASE_URL = prepare_async_db_url(SYNC_DATABASE_URL)



# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create sync engine (keeping the original for backward compatibility)
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create both session factories - keep the original name for sync compatibility
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False, 
    autoflush=False
)

# Async dependency for FastAPI
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()





# Keep the original synchronous dependency working
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



async def get_user_db(session: AsyncSession = Depends(get_async_db)):
    """
    Async dependency function that provides a SQLAlchemyUserDatabase instance
    for FastAPI-Users, using the asynchronous session.
    """
    yield SQLAlchemyUserDatabase(session, User)

