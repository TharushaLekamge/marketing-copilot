"""GenerationRecord model."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class GenerationRecord(Base):
    """GenerationRecord model for tracking content generation requests and responses."""

    __tablename__ = "generation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt = Column(Text, nullable=False)
    response = Column(JSONB, nullable=True)  # Stores full response with variants (nullable for pending/processing)
    model = Column(String(255), nullable=False)
    tokens = Column(JSONB, nullable=True)  # Stores token usage: {"prompt": 120, "completion": 320}
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )  # Status: pending, processing, completed, failed
    error_message = Column(Text, nullable=True)  # Error message if status is failed
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project = relationship("Project", backref="generation_records")
    user = relationship("User", backref="generation_records")

    def __repr__(self) -> str:
        """String representation of GenerationRecord."""
        return (
            f"<GenerationRecord("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"user_id={self.user_id}, "
            f"model={self.model})>"
        )
