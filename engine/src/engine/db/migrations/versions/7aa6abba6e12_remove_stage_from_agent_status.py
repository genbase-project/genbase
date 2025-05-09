"""remove stage from agent status

Revision ID: 7aa6abba6e12
Revises: 38bd098ff590
Create Date: 2025-04-05 10:42:56.803432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7aa6abba6e12'
down_revision: Union[str, None] = '38bd098ff590'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('agent_status', 'stage')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('agent_status', sa.Column('stage', postgresql.ENUM('INITIALIZE', 'MAINTAIN', 'REMOVE', name='agent_stage'), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
