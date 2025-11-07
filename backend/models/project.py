"""Project model."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from backend.database import Base


class Project(Base):
    """Project model for organizing marketing campaigns and assets."""

    __tablename__ = "projects"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
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
    owner = relationship("User", backref="projects")

    def __repr__(self) -> str:
        """String representation of Project."""
        return f"<Project(id={self.id}, name={self.name}, owner_id={self.owner_id})>"
