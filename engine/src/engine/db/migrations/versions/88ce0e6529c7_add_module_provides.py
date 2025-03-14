"""Add module  provides

Revision ID: 88ce0e6529c7
Revises: c356ad4e9aff
Create Date: 2025-03-02 13:25:06.652662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88ce0e6529c7'
down_revision: Union[str, None] = 'c356ad4e9aff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('module_provides',
    sa.Column('provider_id', sa.String(), nullable=False),
    sa.Column('receiver_id', sa.String(), nullable=False),
    sa.Column('resource_type', sa.Enum('WORKSPACE', 'ACTION', name='providetype'), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['modules.module_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['receiver_id'], ['modules.module_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('provider_id', 'receiver_id', 'resource_type')
    )
    op.create_index('idx_module_provides_provider', 'module_provides', ['provider_id'], unique=False)
    op.create_index('idx_module_provides_receiver', 'module_provides', ['receiver_id'], unique=False)
    op.create_index('idx_module_provides_resource', 'module_provides', ['resource_type'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_module_provides_resource', table_name='module_provides')
    op.drop_index('idx_module_provides_receiver', table_name='module_provides')
    op.drop_index('idx_module_provides_provider', table_name='module_provides')
    op.drop_table('module_provides')
    # ### end Alembic commands ###
