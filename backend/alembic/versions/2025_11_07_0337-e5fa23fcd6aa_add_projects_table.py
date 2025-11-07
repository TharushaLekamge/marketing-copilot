"""add_projects_table

Revision ID: e5fa23fcd6aa
Revises: 2024_01_01_000000
Create Date: 2025-11-07 03:37:33.514875+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5fa23fcd6aa"
down_revision: Union[str, None] = "2024_01_01_000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create projects table."""
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"])


def downgrade() -> None:
    """Drop projects table."""
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
