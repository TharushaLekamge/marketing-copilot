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
    response = Column(JSONB, nullable=False)  # Stores full response with variants
    model = Column(String(255), nullable=False)
    tokens = Column(JSONB, nullable=True)  # Stores token usage: {"prompt": 120, "completion": 320}
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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
