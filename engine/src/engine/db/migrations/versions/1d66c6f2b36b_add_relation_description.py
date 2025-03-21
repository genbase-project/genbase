"""add_relation_description

Revision ID: 1d66c6f2b36b
Revises: 51944779d9a5
Create Date: 2025-01-26 20:10:15.063276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d66c6f2b36b'
down_revision: Union[str, None] = '51944779d9a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('module_relations', sa.Column('description', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('module_relations', 'description')
    # ### end Alembic commands ###
