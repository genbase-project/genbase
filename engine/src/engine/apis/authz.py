# engine/apis/authz.py

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from loguru import logger

# Import User model and DB session for checks
from engine.auth.dependencies import ACT_ASSIGN, ACT_READ_ROLES, ACT_REVOKE, OBJ_USER_ROLE, add_role_for_user, get_roles_for_user, require_action
from engine.db.models import User
from engine.db.session import AsyncSessionLocal


# --- Pydantic Models ---

class AssignRoleRequest(BaseModel):
    role: str = Field(..., description="The name of the role to assign.")

class UserRolesResponse(BaseModel):
    user_id: str
    roles: List[str]

class RoleAssignmentResponse(BaseModel):
    status: str
    message: str
    roles: List[str] # Return updated roles

# --- Authz Router ---

class AuthzRouter:
    """Router for authorization management (roles, policies)."""

    def __init__(self, prefix: str = "/authz"):
        self.router = APIRouter(prefix=prefix, tags=["authorization"])
        self._setup_routes()

    async def _check_user_exists(self, user_id: uuid.UUID):
        """Helper to verify target user exists in DB."""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found.")
            return user

    # --- Route Handler Methods ---
    async def _revoke_role_from_user(
        self,
        user_id: uuid.UUID = Path(..., description="The UUID of the user to revoke the role from."),
        role_name: str = Path(..., description="The name of the role to revoke.")
    ) -> RoleAssignmentResponse:
        """Revokes a specified role from a specific user."""
        await self._check_user_exists(user_id)  # Verify target user exists first
        user_id_str = str(user_id)

        logger.info(f"Attempting to revoke role '{role_name}' from user '{user_id_str}'")
        try:
            # Import the helper function at the top of the file if not already imported
            from engine.auth.dependencies import remove_role_for_user
            
            # Remove the role from the user
            removed = await remove_role_for_user(user_id_str, role_name)
            if not removed:
                # This might happen if the role wasn't assigned in the first place
                logger.warning(f"Role '{role_name}' may not be assigned to user '{user_id_str}'.")
                # Return a specific message for this case
                return RoleAssignmentResponse(
                    status="warning",
                    message=f"Role '{role_name}' was not assigned to user '{user_id_str}'.",
                    roles=get_roles_for_user(user_id_str)
                )

            # Get updated roles after revocation
            updated_roles = get_roles_for_user(user_id_str)  # Sync read is ok here

            return RoleAssignmentResponse(
                status="success",
                message=f"Role '{role_name}' revoked from user '{user_id_str}'.",
                roles=updated_roles
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to revoke role.")
        
        
    async def _assign_role_to_user(
        self,
        user_id: uuid.UUID = Path(..., description="The UUID of the user to assign the role to."),
        request: AssignRoleRequest = Body(...)
    ) -> RoleAssignmentResponse:
        """Assigns a specified role to a specific user."""
        await self._check_user_exists(user_id) # Verify target user exists first
        user_id_str = str(user_id)
        role_name = request.role

        logger.info(f"Attempting to assign role '{role_name}' to user '{user_id_str}'")
        try:
            # Use the helper function from authorization.py
            added = await add_role_for_user(user_id_str, role_name)
            if not added:
                # This might happen if the role was already assigned
                logger.warning(f"Role '{role_name}' may already be assigned to user '{user_id_str}'.")
                # Still return success, but maybe a different message?

            # Get updated roles
            updated_roles = get_roles_for_user(user_id_str) # Sync read is ok here

            return RoleAssignmentResponse(
                status="success",
                message=f"Role '{role_name}' assigned to user '{user_id_str}'.",
                roles=updated_roles
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to assign role.")

    async def _get_user_roles(
        self,
        user_id: uuid.UUID = Path(..., description="The UUID of the user whose roles to retrieve.")
    ) -> UserRolesResponse:
        """Retrieves the list of roles assigned to a specific user."""
        await self._check_user_exists(user_id) # Verify target user exists
        user_id_str = str(user_id)

        logger.info(f"Getting roles for user '{user_id_str}'")
        try:
            roles = get_roles_for_user(user_id_str) # Sync read is ok
            return UserRolesResponse(user_id=user_id_str, roles=roles)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to retrieve user roles.")

    # --- Setup Routes ---
    def _setup_routes(self):
        """Setup authorization management routes with permissions."""
        self.router.add_api_route(
            "/users/{user_id}/roles",
            self._assign_role_to_user,
            methods=["POST"],
            response_model=RoleAssignmentResponse,
            summary="Assign a role to a user",
            # Requires 'assign' action on 'user_role' object
            dependencies=require_action(OBJ_USER_ROLE, ACT_ASSIGN)
        )

        self.router.add_api_route(
            "/users/{user_id}/roles",
            self._get_user_roles,
            methods=["GET"],
            response_model=UserRolesResponse,
            summary="Get roles assigned to a user",
            # Requires 'read' action on 'user_role' object
            dependencies=require_action(OBJ_USER_ROLE, ACT_READ_ROLES)
        )

        self.router.add_api_route(
            "/users/{user_id}/roles/{role_name}",
            self._revoke_role_from_user, # Need to implement this handler
            methods=["DELETE"],
            summary="Revoke a role from a user",
            dependencies=require_action(OBJ_USER_ROLE, ACT_REVOKE)
        )

# --- End of engine/apis/authz.py ---