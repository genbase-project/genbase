from fastapi import Depends, HTTPException, status
from loguru import logger

# Assuming User model and current_active_user are defined as before
from engine.db.models import User
from engine.auth.users import current_active_user

# Import the enforcer instance we created
from engine.auth.casbin_setup import enforcer
import casbin # Import casbin itself for type hinting if needed

def get_enforcer() -> casbin.Enforcer:
    """FastAPI dependency to get the Casbin Enforcer instance."""
    return enforcer

def require_permission(obj: str, act: str):
    """
    Factory for creating a FastAPI dependency that checks user permissions.

    Args:
        obj: The resource (object) the user is trying to access (e.g., "/projects", "/kits/my-kit").
        act: The tool the user is trying to perform (e.g., "read", "create", "delete").

    Returns:
        A FastAPI dependency function.
    """
    async def permission_checker(
        user: User = Depends(current_active_user),
        enforcer_instance: casbin.Enforcer = Depends(get_enforcer)
    ):
        """
        The actual dependency function that performs the permission check.
        """
        user_id = str(user.id)

        logger.debug(f"Checking permission for user '{user_id}' on object '{obj}' with tool '{act}'")

        has_permission = enforcer_instance.enforce(user_id, obj, act)

        if not has_permission:
            # As a fallback, always allow superusers
            if user.is_superuser:
                logger.warning(f"Superuser '{user_id}' granted access to '{obj}' ({act}) via superuser status.")
                return user # Allow access

            logger.warning(f"Permission denied for user '{user_id}' on object '{obj}' with tool '{act}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this tool."
            )

        logger.info(f"Permission granted for user '{user_id}' on object '{obj}' with tool '{act}'")
        return user # Return the user object if needed by the route function

    return permission_checker # Return the inner function