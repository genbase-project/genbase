from datetime import datetime, UTC
from typing import List, Optional, Union
import uuid

from loguru import logger
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound

from engine.db.models import ModuleApiKey
from engine.db.session import SessionLocal


class ApiKeyService:
    """Service for managing API keys"""
    
    def _get_db(self):
        return SessionLocal()
    
    def create_api_key(self, module_id: str, description: Optional[str] = None) -> ModuleApiKey:
        """
        Create a new API key for a module.
        If the module already has an active key, it will be revoked first.
        
        Args:
            module_id: ID of the module
            description: Optional description for the key
            
        Returns:
            The created API key
        """
        with self._get_db() as db:
            # First, revoke any existing active keys for this module
            db.query(ModuleApiKey).filter(
                ModuleApiKey.module_id == module_id,
                ModuleApiKey.is_active == True
            ).update({"is_active": False})
            
            # Create new key
            api_key = ModuleApiKey(
                module_id=module_id,
                api_key=ModuleApiKey.generate_key(),
                description=description,
                is_active=True
            )
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            
            logger.info(f"Created API key for module {module_id}")
            return api_key
    
    def get_api_key(self, module_id: str) -> Optional[ModuleApiKey]:
        """
        Get the active API key for a module
        
        Args:
            module_id: ID of the module
            
        Returns:
            The active API key or None if not found
        """
        with self._get_db() as db:
            query = select(ModuleApiKey).where(
                ModuleApiKey.module_id == module_id,
                ModuleApiKey.is_active
            )
            result = db.execute(query)
            return result.scalars().first()
    
    def revoke_api_key(self, module_id: str) -> bool:
        """
        Revoke the active API key for a module
        
        Args:
            module_id: ID of the module
            
        Returns:
            True if a key was revoked, False if no active key found
        """
        with self._get_db() as db:
            query = update(ModuleApiKey).where(
                ModuleApiKey.module_id == module_id,
                ModuleApiKey.is_active == True
            ).values(
                is_active=False
            )
            result = db.execute(query)
            db.commit()
            
            return result.rowcount > 0
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate an API key and return the associated module ID
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Module ID if key is valid, None otherwise
        """
        with self._get_db() as db:
            try:
                key_obj = db.query(ModuleApiKey).filter(
                    ModuleApiKey.api_key == api_key,
                    ModuleApiKey.is_active == True
                ).one()
                
                # Update last used timestamp
                key_obj.last_used_at = datetime.now(UTC)
                db.commit()
                
                return key_obj.module_id
            except NoResultFound:
                return None