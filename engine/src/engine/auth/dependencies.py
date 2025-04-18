# engine/auth/authorization.py

import os
from pathlib import Path
from fastapi import Depends, HTTPException, status
from loguru import logger
import casbin
import casbin_sqlalchemy_adapter

# Import DB models and User management components needed
from engine.db.models import User
from engine.auth.users import current_active_user # Dependency to get current user
from engine.db.session import SYNC_DATABASE_URL
# Import the function responsible for seeding (defined elsewhere)
from engine.auth.superuser import create_default_superuser

# --- Casbin Enforcer Initialization ---

MODEL_PATH = Path(__file__).parent.parent / "rbac_model.conf"




if not MODEL_PATH.exists():
    logger.critical(f"Casbin model file not found at: {MODEL_PATH}")
    raise FileNotFoundError(f"Casbin model file not found at: {MODEL_PATH}")

adapter = casbin_sqlalchemy_adapter.Adapter(SYNC_DATABASE_URL)
logger.info(f"Casbin SQLAlchemy adapter initialized using URL from DB session.")
enforcer = casbin.Enforcer(str(MODEL_PATH), adapter)
logger.info(f"Casbin Enforcer initialized with model: {MODEL_PATH}")
enforcer.load_policy() # Load policies explicitly at startup
logger.info("Casbin policies loaded via adapter.")


# --- Optional Casbin Helper Functions ---
# These wrap common enforcer actions and ensure policies are saved

async def add_policy(sub: str, obj: str, act: str) -> bool:
    """Adds a policy rule and saves."""
    logger.debug(f"Adding policy: sub='{sub}', obj='{obj}', act='{act}'")
    added = enforcer.add_policy(sub, obj, act)
    if added:
        enforcer.save_policy()
        logger.info(f"Policy added and saved: ('{sub}', '{obj}', '{act}')")
    else:
        logger.warning(f"Policy ('{sub}', '{obj}', '{act}') already exists or failed to add.")
    return added

async def remove_policy(sub: str, obj: str, act: str) -> bool:
    """Removes a policy rule and saves."""
    logger.debug(f"Removing policy: sub='{sub}', obj='{obj}', act='{act}'")
    # Note: remove_policy might require filtering if multiple identical policies exist
    # For typical RBAC, remove_filtered_policy is safer if duplicates are possible.
    # removed = enforcer.remove_policy(sub, obj, act) # Returns bool in recent versions
    # Using filtered remove is generally safer if duplicates aren't expected but possible
    removed_count = enforcer.remove_filtered_policy(0, sub, obj, act) # field_index 0 is 'sub'
    removed = removed_count > 0
    if removed:
        enforcer.save_policy()
        logger.info(f"Policy removed and saved: ('{sub}', '{obj}', '{act}')")
    else:
        logger.warning(f"Policy ('{sub}', '{obj}', '{act}') not found or failed to remove.")
    return removed

async def add_role_for_user(user_id: str, role: str) -> bool:
    """Assigns a role to a user and saves."""
    logger.debug(f"Assigning role '{role}' to user '{user_id}'")
    added = enforcer.add_grouping_policy(user_id, role)
    if added:
        enforcer.save_policy()
        logger.info(f"Role '{role}' assigned to user '{user_id}' and saved.")
    else:
        logger.warning(f"Role '{role}' already assigned to user '{user_id}' or failed to assign.")
    return added

async def remove_role_for_user(user_id: str, role: str) -> bool:
    """Removes a role assignment from a user and saves."""
    logger.debug(f"Removing role '{role}' from user '{user_id}'")
    removed = enforcer.remove_grouping_policy(user_id, role)
    if removed:
        enforcer.save_policy()
        logger.info(f"Role '{role}' removed from user '{user_id}' and saved.")
    else:
        logger.warning(f"Role '{role}' not assigned to user '{user_id}' or failed to remove.")
    return removed

def get_roles_for_user(user_id: str) -> list[str]:
    """Gets the roles assigned to a user (sync read is often OK)."""
    logger.debug(f"Getting roles for user '{user_id}'")
    return enforcer.get_roles_for_user(user_id)

# --- FastAPI Dependencies ---

def get_enforcer() -> casbin.Enforcer:
    """FastAPI dependency to get the globally initialized Casbin Enforcer."""
    if not enforcer:
        raise RuntimeError("Casbin enforcer not initialized.")
    return enforcer

def require_permission(obj: str, act: str):
    async def permission_checker(
        user: User = Depends(current_active_user),
        enforcer_instance: casbin.Enforcer = Depends(get_enforcer)
    ):
        user_id = str(user.id)
        
        # Reload policies to ensure we have the latest
        enforcer_instance.load_policy()
        
        has_permission = enforcer_instance.enforce(user_id, obj, act)


        if not has_permission:
            if user.is_superuser:
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Action '{act}' on resource '{obj}' is not allowed."
            )
        return user
    return permission_checker

# --- Startup Function ---

async def setup_authorization_on_startup():
    """
    Performs authorization-related setup during application startup.
    - Reloads policies from adapter.
    - Calls the superuser seeding function.
    """
    logger.info("Running authorization setup on startup...")
    try:
        # Reload policies from adapter to ensure enforcer is in sync before seeding
        enforcer.load_policy()
        logger.info("Casbin policies reloaded from adapter.")

        # Call the function responsible for creating DB user and seeding Casbin policies
        create_default_superuser()

        logger.info("Authorization setup complete.")
    except Exception as e:
        logger.error(f"Error during authorization setup on startup: {e}", exc_info=True)
        # Depending on severity, you might re-raise or handle differently
        # raise RuntimeError("Authorization setup failed") from e











# --- Include Routers with Permissions ---
# (Keep constants and helper function here for clarity when adding routers)
OBJ_KIT = "kit"
OBJ_MODULE = "module"
OBJ_WORKSPACE = "workspace"
OBJ_PROJECT = "project"
OBJ_RESOURCE = "resource"
OBJ_MODEL = "model"
OBJ_PROFILE = "profile"
OBJ_EMBEDDING = "embedding"
OBJ_CHAT = "chat"
OBJ_USER = "user"
ACT_LIST = "list"
ACT_READ = "read"
ACT_CREATE = "create"
ACT_UPDATE = "update"
ACT_DELETE = "delete"
ACT_EXECUTE = "execute"
ACT_STREAM = "stream"
OBJ_USER_ROLE = "user_role" # Object representing user role assignments
ACT_ASSIGN = "assign"     # Action for assigning a role
ACT_REVOKE = "revoke"     # Action for revoking a role (optional for now)
ACT_READ_ROLES = "read" # Action for reading a user's roles



def require_action(resource_obj: str, base_action: str):
    """Helper to apply the require_permission dependency."""
    # Use the imported require_permission
    return [Depends(require_permission(resource_obj, base_action))]
