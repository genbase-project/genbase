import os
import traceback
from fastapi_users.password import PasswordHelper
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from engine.db.models import User
import uuid

# Add this to your imports at the top
from fastapi_users.exceptions import UserAlreadyExists

from engine.db.session import AsyncSessionLocal

async def create_default_superuser():
    """Create a default superuser using ADMIN_USER and ADMIN_PASSWORD environment variables"""
    try:
        admin_user = os.getenv("ADMIN_USER")
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        if not admin_user or not admin_password:
            logger.warning("ADMIN_USER or ADMIN_PASSWORD environment variables not set. Skipping default superuser creation.")
            return
            
        logger.info(f"Checking if admin user '{admin_user}' exists...")
        
        # Create an async session
        async with AsyncSessionLocal() as session:
            # Check if user already exists
            query = select(User).where(User.email == admin_user)
            result = await session.execute(query)
            existing_user = result.scalars().first()
            
            if existing_user:
                logger.info(f"Admin user '{admin_user}' already exists.")
                
                # If user exists but is not a superuser, update it
                if not existing_user.is_superuser:
                    logger.info(f"Setting '{admin_user}' as superuser...")
                    existing_user.is_superuser = True
                    session.add(existing_user)
                    await session.commit()
                    logger.info(f"User '{admin_user}' is now a superuser.")
                
                return
            
            # User doesn't exist, create it
            password_helper = PasswordHelper()
            hashed_password = password_helper.hash(admin_password)
            
            # Create new superuser
            new_user = User(
                id=uuid.uuid4(),
                email=admin_user,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
                is_verified=True  # Set as verified
            )
            
            session.add(new_user)
            await session.commit()
            
            logger.info(f"Default superuser '{admin_user}' created successfully.")
    
    except Exception as e:
        logger.error(f"Error creating default superuser: {str(e)}")
        logger.error(traceback.format_exc())