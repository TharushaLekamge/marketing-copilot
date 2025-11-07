"""Project schemas."""

from pydantic import BaseModel, ConfigDict, field_validator


class ProjectCreate(BaseModel):
    """Project creation request schema."""

    name: str
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize name by stripping whitespace."""
        return v.strip() if isinstance(v, str) else v

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: str | None) -> str | None:
        """Normalize description by stripping whitespace."""
        if v is None:
            return None
        return v.strip() if isinstance(v, str) else v


class ProjectUpdate(BaseModel):
    """Project update request schema."""

    name: str | None = None
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        """Normalize name by stripping whitespace."""
        if v is None:
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: str | None) -> str | None:
        """Normalize description by stripping whitespace."""
        if v is None:
            return None
        return v.strip() if isinstance(v, str) else v


class ProjectResponse(BaseModel):
    """Project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str
