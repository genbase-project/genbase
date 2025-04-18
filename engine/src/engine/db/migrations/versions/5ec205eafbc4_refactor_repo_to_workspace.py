"""refactor repo to workspace

Revision ID: 5ec205eafbc4
Revises: 3084ae1366e8
Create Date: 2025-04-18 06:04:50.180869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ec205eafbc4'
down_revision: Union[str, None] = '3084ae1366e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Rename repo_name to workspace_name
    op.alter_column('modules', 'repo_name', new_column_name='workspace_name')
    # Removed the drop_table for casbin_rule

def downgrade() -> None:
    # Rename workspace_name back to repo_name
    op.alter_column('modules', 'workspace_name', new_column_name='repo_name')
    # Removed the recreation of casbin_rule table