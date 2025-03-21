"""rename tool_data

Revision ID: dde76d5a3ca7
Revises: b3c6f4e02985
Create Date: 2025-02-13 17:48:41.850333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dde76d5a3ca7'
down_revision: Union[str, None] = 'b3c6f4e02985'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_history', sa.Column('tool_calls', sa.JSON(), nullable=True))
    op.drop_column('chat_history', 'tool_data')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_history', sa.Column('tool_data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.drop_column('chat_history', 'tool_calls')
    # ### end Alembic commands ###
