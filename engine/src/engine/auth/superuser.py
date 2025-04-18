# engine/auth/superuser.py
import os
import traceback
import uuid
from fastapi_users.password import PasswordHelper
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.db.models import User
from engine.db.session import AsyncSessionLocal
from engine.auth.casbin_setup import enforcer # Import enforcer

async def create_default_superuser():
    """Create a default superuser using ADMIN_USER/ADMIN_PASSWORD environment variables
       and ensure the 'admin' Casbin role and associated policies are correctly set up."""
    try:
        admin_user_email = os.getenv("ADMIN_USER")
        admin_password = os.getenv("ADMIN_PASSWORD")
        admin_role = "admin" # Define the admin role name
        viewer_role = "viewer" # Define the viewer role name

        if not admin_user_email or not admin_password:
            logger.warning("ADMIN_USER or ADMIN_PASSWORD environment variables not set. Skipping default superuser configuration.")
            return

        logger.info(f"Checking/configuring admin user '{admin_user_email}' with Casbin roles/policies...")

        async with AsyncSessionLocal() as session:
            # --- Find or Create User in DB ---
            query = select(User).where(User.email == admin_user_email)
            result = await session.execute(query)
            existing_user = result.scalars().first()

            user_for_casbin = None
            if existing_user:
                logger.info(f"Admin user '{admin_user_email}' already exists in DB.")
                user_for_casbin = existing_user
                # Ensure DB superuser flag is set (optional, for potential bypasses)
                if not existing_user.is_superuser:
                    logger.info(f"Setting existing user '{admin_user_email}' as database superuser.")
                    existing_user.is_superuser = True
                    session.add(existing_user)
                    await session.commit()
            else:
                # Create the user in DB
                logger.info(f"Creating admin user '{admin_user_email}' in DB...")
                password_helper = PasswordHelper()
                hashed_password = password_helper.hash(admin_password)
                new_user = User(
                    id=uuid.uuid4(), # Generate UUID for the new user
                    email=admin_user_email,
                    hashed_password=hashed_password,
                    is_active=True,
                    is_superuser=True, # Set as database superuser
                    is_verified=True   # Assume verified for admin
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user) # Get the generated ID back
                user_for_casbin = new_user
                logger.info(f"Admin user '{admin_user_email}' created successfully in DB.")

            # --- Casbin Role and Policy Seeding ---
            if user_for_casbin:
                user_id_str = str(user_for_casbin.id) # Use the user's UUID as string

                # Reload policies before making changes to ensure we have the latest state
                enforcer.load_policy()

                # 1. Assign Admin Role to User
                has_role_assigned = enforcer.has_grouping_policy(user_id_str, admin_role)
                if not has_role_assigned:
                    logger.info(f"Assigning Casbin role '{admin_role}' to user '{user_id_str}'")
                    added = enforcer.add_grouping_policy(user_id_str, admin_role)
                    if added:
                        logger.info(f"Role '{admin_role}' assigned to user '{user_id_str}'.")
                        enforcer.save_policy() # Save this change
                    else:
                         logger.warning(f"Failed to assign role '{admin_role}' to user '{user_id_str}'. Already assigned?")
                else:
                    logger.info(f"User '{user_id_str}' already has Casbin role '{admin_role}'.")

                # 2. Ensure Admin Policy Exists (Allow all)
                admin_obj = "*"
                admin_act = "*"
                has_admin_policy = enforcer.has_policy(admin_role, admin_obj, admin_act)
                if not has_admin_policy:
                    logger.info(f"Adding policy for role '{admin_role}': obj='{admin_obj}', act='{admin_act}'")
                    added = enforcer.add_policy(admin_role, admin_obj, admin_act)
                    if added:
                         logger.info(f"Admin policy added: ('{admin_role}', '{admin_obj}', '{admin_act}')")
                         enforcer.save_policy() # Save this change
                    else:
                         logger.warning(f"Failed to add admin policy ('{admin_role}', '{admin_obj}', '{admin_act}').")
                else:
                    logger.info(f"Admin policy ('{admin_role}', '{admin_obj}', '{admin_act}') already exists.")

                # 3. Ensure Viewer Policies Exist (Defines the role's permissions)
                viewer_policies = [
                    (viewer_role, "*", "read"),
                    (viewer_role, "*", "list"),
                    (viewer_role, "*", "stream"),
                ]
                policy_changed = False
                for policy in viewer_policies:
                    has_viewer_policy = enforcer.has_policy(*policy)
                    if not has_viewer_policy:
                        logger.info(f"Adding policy for role '{viewer_role}': obj='{policy[1]}', act='{policy[2]}'")
                        added = enforcer.add_policy(*policy)
                        if added:
                            logger.info(f"Viewer policy added: {policy}")
                            policy_changed = True
                        else:
                            logger.warning(f"Failed to add viewer policy {policy}.")
                    else:
                         logger.info(f"Viewer policy {policy} already exists.")
                if policy_changed:
                    enforcer.save_policy() # Save if any viewer policies were added

            else:
                logger.error("Could not find or create the admin user for Casbin configuration.")

    except Exception as e:
        logger.error(f"Error during default superuser/admin role configuration: {str(e)}")
        logger.error(traceback.format_exc())