"""add_assets_table

Revision ID: 09c1b2742cc7
Revises: 365f9e378fcc
Create Date: 2025-11-07 04:46:13.973340+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "09c1b2742cc7"
down_revision: Union[str, None] = "365f9e378fcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
