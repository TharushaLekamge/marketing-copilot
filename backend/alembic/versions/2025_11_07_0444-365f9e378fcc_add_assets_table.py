"""add_assets_table

Revision ID: 365f9e378fcc
Revises: e5fa23fcd6aa
Create Date: 2025-11-07 04:44:14.343953+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '365f9e378fcc'
down_revision: Union[str, None] = 'e5fa23fcd6aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

