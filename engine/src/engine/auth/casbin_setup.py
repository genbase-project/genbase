# engine/auth/casbin_setup.py

import os
import casbin
import casbin_sqlalchemy_adapter
from pathlib import Path
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
from loguru import logger # Add logger

from engine.db.session import SYNC_DATABASE_URL # Use the existing sync URL

# Adjust the path as necessary - relative to this file's location
MODEL_PATH = Path(__file__).parent.parent / "rbac_model.conf" # Correct path relative to this file

if not MODEL_PATH.exists():
     logger.error(f"Casbin model file not found at: {MODEL_PATH}")
     # Depending on severity, you might want to raise an error or exit
     # raise FileNotFoundError(f"Casbin model file not found at: {MODEL_PATH}")

# --- Adapter and Enforcer Setup ---

# The adapter will automatically create the 'casbin_rule' table if it doesn't exist
try:
    adapter = casbin_sqlalchemy_adapter.Adapter(SYNC_DATABASE_URL)
    logger.info(f"Casbin SQLAlchemy adapter initialized with URL: {SYNC_DATABASE_URL}")
except Exception as e:
     logger.critical(f"Failed to initialize Casbin SQLAlchemy adapter: {e}", exc_info=True)
     raise

# Create the Casbin Enforcer
# It loads the model configuration and uses the adapter for policies
# Policies are loaded from the DB automatically by the adapter upon initialization
# or when methods like enforce() are called if not already loaded.
try:
    enforcer = casbin.Enforcer(str(MODEL_PATH), adapter)
    logger.info(f"Casbin Enforcer initialized with model: {MODEL_PATH}")
    # Load policies explicitly at startup - good practice
    enforcer.load_policy()
    logger.info("Casbin policies loaded from adapter.")
except Exception as e:
     logger.critical(f"Failed to initialize Casbin Enforcer: {e}", exc_info=True)
     raise


# --- Optional Helper Functions (keep or remove as needed) ---

async def add_policy(sub: str, obj: str, act: str) -> bool:
    """Adds a policy rule to the DB."""
    # Use async add_policy for consistency
    added = enforcer.add_policy(sub, obj, act)
    if added:
        enforcer.save_policy() # Ensure persistence
    return added

async def remove_policy(sub: str, obj: str, act: str) -> bool:
    """Removes a policy rule from the DB."""
    removed = enforcer.remove_policy(sub, obj, act)
    if removed:
        enforcer.save_policy() # Ensure persistence
    return removed

async def add_role_for_user(user_id: str, role: str) -> bool:
    """Assigns a role to a user."""
    added = enforcer.add_grouping_policy(user_id, role)
    if added:
        enforcer.save_policy() # Ensure persistence
    return added

async def remove_role_for_user(user_id: str, role: str) -> bool:
    """Removes a role assignment from a user."""
    removed = enforcer.remove_grouping_policy(user_id, role)
    if removed:
        enforcer.save_policy() # Ensure persistence
    return removed

def get_roles_for_user(user_id: str) -> list[str]:
    """Gets the roles assigned to a user (sync version ok for reads)."""
    return enforcer.get_roles_for_user(user_id)

async def check_permission(user_id: str, obj: str, act: str) -> bool:
    """Checks if a user has permission (use async enforce)."""
    # Reload policy before enforcing if you suspect changes elsewhere
    # enforcer.load_policy()
    return enforcer.enforce(user_id, obj, act)