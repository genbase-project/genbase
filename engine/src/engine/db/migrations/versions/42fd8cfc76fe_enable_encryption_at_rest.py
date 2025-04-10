"""enable encryption at rest

Revision ID: 42fd8cfc76fe
Revises: 195d959d6699
Create Date: 2025-04-09 16:53:49.049350

"""
import os
import json
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column
from sqlalchemy.orm import Session

# --- WARNING: Requires cryptography and the key! ---
# Ensure cryptography is installed in the env running migrations
# You MUST make the exact same encryption key available here
# as the one used by your application (e.g., via env var)
try:
    from cryptography.fernet import Fernet, InvalidToken
    ENCRYPTION_KEY_ENV_VAR = "ENV_ENCRYPTION_KEY" # Use the SAME name as your app
    _encryption_key_str = os.environ.get(ENCRYPTION_KEY_ENV_VAR)
    if not _encryption_key_str:
        raise RuntimeError(f"FATAL: Migration requires environment variable '{ENCRYPTION_KEY_ENV_VAR}' to be set.")
    _fernet = Fernet(_encryption_key_str.encode('utf-8'))
    CRYPTO_AVAILABLE = True
    print(f"Migration {__name__}: Encryption key loaded successfully.")
except ImportError:
    _fernet = None
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography library not found. Cannot perform data en/decryption.")
    print("Migration will only change column types, existing data will be incompatible.")
except Exception as e:
    _fernet = None
    CRYPTO_AVAILABLE = False
    print(f"ERROR loading encryption key for migration: {e}")
    raise RuntimeError("Failed to initialize encryption for migration.") from e
# --- End WARNING ---


# revision identifiers, used by Alembic.
revision: str = '42fd8cfc76fe'
down_revision: Union[str, None] = '195d959d6699'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table structure for data migration step
modules_table = table('modules',
    column('module_id', sa.String), # Adjust type if needed, only need PK
    column('env_vars', sa.JSON),     # The original type for reading
    column('env_vars_encrypted', sa.Text) # The temporary/new column
)

modules_table_encrypted = table('modules',
    column('module_id', sa.String),
    column('env_vars', sa.Text), # Type during downgrade reading
    column('env_vars_decrypted', sa.JSON) # temp column for downgrade
)


def upgrade() -> None:
    if not CRYPTO_AVAILABLE or not _fernet:
        raise RuntimeError("Cannot perform upgrade without cryptography library and a valid key.")

    print("Starting upgrade: Encrypting modules.env_vars")
    bind = op.get_bind()
    session = Session(bind=bind)

    # 1. Add the new TEXT column (temporarily nullable if needed, or handle defaults)
    op.add_column('modules', sa.Column('env_vars_encrypted', sa.Text(), nullable=True))
    print("Added temporary column: env_vars_encrypted")

    # 2. Iterate and encrypt data
    #    IMPORTANT: Process in batches for large tables
    batch_size = 100
    offset = 0
    while True:
        print(f"Processing batch starting at offset {offset}...")
        # Select rows using the defined table structure
        modules_to_process = session.query(
                modules_table.c.module_id,
                modules_table.c.env_vars
            ).where(
                modules_table.c.env_vars != None # noqa Process non-null JSON
            ).order_by(modules_table.c.module_id).limit(batch_size).offset(offset).all()

        if not modules_to_process:
            print("No more modules to process.")
            break

        print(f"Found {len(modules_to_process)} modules in batch.")
        updates = []
        for module_id, env_vars_json in modules_to_process:
            if not isinstance(env_vars_json, dict):
                 print(f"Skipping module {module_id}: env_vars is not a dict ({type(env_vars_json)}).")
                 # Or handle lists/other types if they were possible
                 continue
            try:
                json_string = json.dumps(env_vars_json)
                encrypted_bytes = _fernet.encrypt(json_string.encode('utf-8'))
                encrypted_string = encrypted_bytes.decode('utf-8')
                updates.append({'b_module_id': module_id, 'b_env_vars_encrypted': encrypted_string})
            except Exception as e:
                logging.error(f"Failed to encrypt env_vars for module {module_id}: {e}", exc_info=True)
                # Decide how to handle errors: skip? fail migration?
                raise RuntimeError(f"Encryption failed for module {module_id}") from e

        if updates:
             # Execute batch update using core SQLAlchemy update (more efficient)
             stmt = modules_table.update().where(
                 modules_table.c.module_id == sa.bindparam('b_module_id')
             ).values(
                 env_vars_encrypted=sa.bindparam('b_env_vars_encrypted')
             )
             session.execute(stmt, updates)
             print(f"Updated {len(updates)} modules in batch.")

        session.commit() # Commit each batch
        offset += batch_size

    # 3. Drop the old JSON column
    #    BACKUP YOUR DATABASE BEFORE THIS STEP!
    op.drop_column('modules', 'env_vars')
    print("Dropped original column: env_vars")

    # 4. Rename the new column to the original name
    op.alter_column('modules', 'env_vars_encrypted', new_column_name='env_vars', nullable=False)
    print("Renamed env_vars_encrypted to env_vars")

    session.close()
    print("Upgrade complete.")


def downgrade() -> None:
    # Downgrade is the reverse: TEXT (encrypted) -> JSON (decrypted)
    if not CRYPTO_AVAILABLE or not _fernet:
        raise RuntimeError("Cannot perform downgrade without cryptography library and a valid key.")

    print("Starting downgrade: Decrypting modules.env_vars")
    bind = op.get_bind()
    session = Session(bind=bind)

    # 1. Add temporary JSON column
    #    (Use JSONB if that was your original default on Postgres)
    op.add_column('modules', sa.Column('env_vars_decrypted', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    print("Added temporary column: env_vars_decrypted")


    # 2. Iterate and decrypt data
    batch_size = 100
    offset = 0
    while True:
        print(f"Processing downgrade batch starting at offset {offset}...")
        modules_to_process = session.query(
                modules_table_encrypted.c.module_id,
                modules_table_encrypted.c.env_vars # Reading from the current 'env_vars' (TEXT)
            ).where(
                modules_table_encrypted.c.env_vars != None # noqa Process non-null text
            ).order_by(modules_table_encrypted.c.module_id).limit(batch_size).offset(offset).all()

        if not modules_to_process:
            print("No more modules to process for downgrade.")
            break

        print(f"Found {len(modules_to_process)} modules in batch.")
        updates = []
        for module_id, env_vars_encrypted_text in modules_to_process:
            try:
                decrypted_bytes = _fernet.decrypt(env_vars_encrypted_text.encode('utf-8'))
                json_string = decrypted_bytes.decode('utf-8')
                decrypted_json = json.loads(json_string)
                updates.append({'b_module_id': module_id, 'b_env_vars_decrypted': decrypted_json})
            except InvalidToken:
                logging.error(f"Failed to decrypt env_vars for module {module_id}: Invalid token (wrong key or data corruption?).")
                 # Decide handling: Set NULL? Skip? Fail? Setting NULL might be safest if key is wrong.
                updates.append({'b_module_id': module_id, 'b_env_vars_decrypted': None})
                # Or: raise RuntimeError(f"Decryption failed for module {module_id}: Invalid Token")
            except Exception as e:
                logging.error(f"Failed to decrypt or parse env_vars for module {module_id}: {e}", exc_info=True)
                raise RuntimeError(f"Decryption/parsing failed for module {module_id}") from e

        if updates:
            stmt = modules_table_encrypted.update().where(
                modules_table_encrypted.c.module_id == sa.bindparam('b_module_id')
            ).values(
                env_vars_decrypted=sa.bindparam('b_env_vars_decrypted')
            )
            session.execute(stmt, updates)
            print(f"Updated {len(updates)} modules in downgrade batch.")

        session.commit()
        offset += batch_size

    # 3. Drop the encrypted TEXT column
    #    BACKUP YOUR DATABASE BEFORE THIS STEP!
    op.drop_column('modules', 'env_vars')
    print("Dropped encrypted text column: env_vars")


    # 4. Rename the temporary column back to original name
    op.alter_column('modules', 'env_vars_decrypted', new_column_name='env_vars', nullable=False)
    print("Renamed env_vars_decrypted to env_vars")

    session.close()
    print("Downgrade complete.")