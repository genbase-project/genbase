# engine/auth/casbin_setup.py

import os
import casbin
import casbin_sqlalchemy_adapter
from pathlib import Path
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker

from engine.db.session import SYNC_DATABASE_URL # Use the existing sync URL

# Adjust the path as necessary
MODEL_PATH = Path(__file__).parent.parent.parent / "rbac_model.conf"
# Alternatively, use an absolute path or environment variable


# --- Adapter and Enforcer Setup ---

# The adapter will automatically create the 'casbin_rule' table if it doesn't exist
adapter = casbin_sqlalchemy_adapter.Adapter(SYNC_DATABASE_URL)

# Create the Casbin Enforcer
# It loads the model configuration and uses the adapter for policies
# Policies are loaded from the DB automatically by the adapter upon initialization
# or when methods like enforce() are called if not already loaded.
enforcer = casbin.Enforcer(str(MODEL_PATH), adapter)

def add_policy(sub: str, obj: str, act: str) -> bool:
    """Adds a policy rule to the DB."""
    return enforcer.add_policy(sub, obj, act)

def remove_policy(sub: str, obj: str, act: str) -> bool:
    """Removes a policy rule from the DB."""
    return enforcer.remove_policy(sub, obj, act)

def add_role_for_user(user_id: str, role: str) -> bool:
    """Assigns a role to a user."""
    # Note: In Casbin, user IDs and role names are typically strings
    return enforcer.add_grouping_policy(user_id, role)

def remove_role_for_user(user_id: str, role: str) -> bool:
    """Removes a role assignment from a user."""
    return enforcer.remove_grouping_policy(user_id, role)

def get_roles_for_user(user_id: str) -> list[str]:
    """Gets the roles assigned to a user."""
    return enforcer.get_roles_for_user(user_id)

def check_permission(user_id: str, obj: str, act: str) -> bool:
    """Checks if a user has permission."""
    return enforcer.enforce(user_id, obj, act)


print(f"Casbin Enforcer initialized with model: {MODEL_PATH} and SQLAlchemy adapter.")

