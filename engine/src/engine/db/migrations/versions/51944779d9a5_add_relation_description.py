"""add_relation_description

Revision ID: 51944779d9a5
Revises: 80a345d4c6d4
Create Date: 2025-01-26 20:06:14.484846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51944779d9a5'
down_revision: Union[str, None] = '80a345d4c6d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
