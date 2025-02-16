"""remove workfloe data table

Revision ID: b308bde3bf12
Revises: efaa991ab7bd
Create Date: 2025-02-16 13:20:00.916020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b308bde3bf12'
down_revision: Union[str, None] = 'efaa991ab7bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_workflow_lookup', table_name='workflow_data')
    op.drop_table('workflow_data')
    op.drop_constraint('fk_workflow_stores_module_id', 'workflow_stores', type_='foreignkey')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key('fk_workflow_stores_module_id', 'workflow_stores', 'modules', ['module_id'], ['module_id'], ondelete='CASCADE')
    op.create_table('workflow_data',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('module_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('workflow_type', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('collection', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['modules.module_id'], name='workflow_data_module_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='workflow_data_pkey'),
    sa.UniqueConstraint('module_id', 'workflow_type', 'collection', name='unique_workflow_data')
    )
    op.create_index('idx_workflow_lookup', 'workflow_data', ['module_id', 'workflow_type', 'collection'], unique=False)
    # ### end Alembic commands ###
