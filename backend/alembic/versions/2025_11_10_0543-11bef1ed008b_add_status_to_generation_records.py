"""add_status_to_generation_records

Revision ID: 11bef1ed008b
Revises: bac97f151d97
Create Date: 2025-11-10 05:43:01.790784+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "11bef1ed008b"
down_revision: Union[str, None] = "bac97f151d97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make response nullable (for pending/processing status)
    op.alter_column("generation_records", "response", nullable=True)

    # Add status column with default 'pending'
    op.add_column(
        "generation_records",
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )

    # Add error_message column
    op.add_column(
        "generation_records",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # Add updated_at column
    op.add_column(
        "generation_records",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create index on status for faster queries
    op.create_index(
        op.f("ix_generation_records_status"),
        "generation_records",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f("ix_generation_records_status"), table_name="generation_records")

    # Drop columns
    op.drop_column("generation_records", "updated_at")
    op.drop_column("generation_records", "error_message")
    op.drop_column("generation_records", "status")

    # Make response non-nullable again
    op.alter_column("generation_records", "response", nullable=False)
