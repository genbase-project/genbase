"""add_relation_description

Revision ID: 80a345d4c6d4
Revises: 7e0a1909e829
Create Date: 2025-01-26 19:38:12.116187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80a345d4c6d4'
down_revision: Union[str, None] = '7e0a1909e829'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
