"""disable migration on casbin_rule table object

Revision ID: 8b8675857e62
Revises: 5ec205eafbc4
Create Date: 2025-04-18 06:11:19.606218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b8675857e62'
down_revision: Union[str, None] = '5ec205eafbc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
