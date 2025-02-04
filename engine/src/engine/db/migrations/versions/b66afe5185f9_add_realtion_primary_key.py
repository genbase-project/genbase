"""add realtion primary key

Revision ID: b66afe5185f9
Revises: 77139f76018f
Create Date: 2025-01-31 22:13:18.191155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b66afe5185f9'
down_revision: Union[str, None] = '77139f76018f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing primary key
    op.drop_constraint('module_relations_pkey', 'module_relations', type_='primary')
    
    # Add new composite primary key
    op.create_primary_key(
        'module_relations_pkey',
        'module_relations',
        ['source_id', 'target_id', 'relation_type']
    )

def downgrade() -> None:
    # Drop new primary key
    op.drop_constraint('module_relations_pkey', 'module_relations', type_='primary')
    
    # Restore original primary key
    op.create_primary_key(
        'module_relations_pkey',
        'module_relations',
        ['source_id', 'target_id']
    )
