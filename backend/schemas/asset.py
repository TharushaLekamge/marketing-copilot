"""Asset schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetCreate(BaseModel):
    """Schema for creating a new asset."""

    filename: str = Field(..., min_length=1, max_length=255, description="Name of the file")
    content_type: str = Field(..., min_length=1, max_length=100, description="MIME type of the file")
    metadata: Optional[dict] = Field(None, description="Optional metadata for the asset")

    @field_validator("filename", mode="before")
    @classmethod
    def normalize_filename(cls, v: str) -> str:
        """Normalize filename by stripping whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("content_type", mode="before")
    @classmethod
    def normalize_content_type(cls, v: str) -> str:
        """Normalize content type by stripping whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v


class AssetUpdate(BaseModel):
    """Schema for updating an existing asset."""

    filename: Optional[str] = Field(None, min_length=1, max_length=255, description="New name for the asset file")
    content_type: Optional[str] = Field(None, min_length=1, max_length=100, description="New MIME type of the asset")
    ingested: Optional[bool] = Field(None, description="Whether the asset has been ingested")
    metadata: Optional[dict] = Field(None, description="New JSON metadata for the asset")

    @field_validator("filename", mode="before")
    @classmethod
    def normalize_filename(cls, v: Optional[str]) -> Optional[str]:
        """Normalize filename by stripping whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("content_type", mode="before")
    @classmethod
    def normalize_content_type(cls, v: Optional[str]) -> Optional[str]:
        """Normalize content type by stripping whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v


class AssetResponse(BaseModel):
    """Schema for returning asset information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier of the asset")
    project_id: UUID = Field(..., description="ID of the project that owns the asset")
    filename: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type of the file")
    ingested: bool = Field(..., description="Whether the asset has been ingested")
    ingesting: bool = Field(..., description="Whether the asset is currently being ingested")
    asset_metadata: Optional[dict] = Field(None, description="Metadata for the asset")
    created_at: datetime = Field(..., description="Timestamp when the asset was created")
    updated_at: datetime = Field(..., description="Timestamp when the asset was last updated")


class IngestionResponse(BaseModel):
    """Schema for ingestion endpoint response."""

    message: str = Field(..., description="Status message")
    asset_id: UUID = Field(..., description="ID of the asset being ingested")
    ingesting: bool = Field(..., description="Whether ingestion has started")