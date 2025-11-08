"""Add ingesting field to assets table

Revision ID: 20250102_000000
Revises: 20250101_000000
Create Date: 2025-01-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250102_000000"
down_revision: Union[str, None] = "20250101_000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ingesting column to assets table
    op.add_column("assets", sa.Column("ingesting", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    # Remove ingesting column from assets table
    op.drop_column("assets", "ingesting")

