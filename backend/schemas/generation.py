"""Schemas for content generation."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request schema for content generation."""

    project_id: UUID = Field(..., description="ID of the project")
    brief: str = Field(..., description="Campaign brief or description", min_length=1)
    brand_tone: Optional[str] = Field(None, description="Brand tone and style guidelines")
    audience: Optional[str] = Field(None, description="Target audience description")
    objective: Optional[str] = Field(None, description="Campaign objective")
    channels: Optional[list[str]] = Field(None, description="Target channels (e.g., social, email)")


class ContentVariant(BaseModel):
    """Schema for a content variant."""

    variant_type: str = Field(..., description="Type of variant (short_form, long_form, cta)")
    content: str = Field(..., description="Generated content")
    character_count: int = Field(..., description="Character count of the content")
    word_count: int = Field(..., description="Word count of the content")


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""

    model: str = Field(..., description="Model used for generation")
    model_info: Dict[str, Any] = Field(..., description="Additional model information")
    project_id: Optional[str] = Field(None, description="Project ID")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    generation_time: Optional[float] = Field(None, description="Generation time in seconds")


class GenerationResponse(BaseModel):
    """Response schema for content generation."""

    generation_id: UUID = Field(..., description="ID of the generation record")
    short_form: str = Field(..., description="Short-form content variant (max 280 chars)")
    long_form: str = Field(..., description="Long-form content variant (150-300 words)")
    cta: str = Field(..., description="CTA-focused content variant")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    variants: Optional[list[ContentVariant]] = Field(None, description="Structured variant information")

    def model_post_init(self, __context: Any) -> None:
        """Calculate variant statistics after initialization."""
        variants = [
            ContentVariant(
                variant_type="short_form",
                content=self.short_form,
                character_count=len(self.short_form),
                word_count=len(self.short_form.split()),
            ),
            ContentVariant(
                variant_type="long_form",
                content=self.long_form,
                character_count=len(self.long_form),
                word_count=len(self.long_form.split()),
            ),
            ContentVariant(
                variant_type="cta",
                content=self.cta,
                character_count=len(self.cta),
                word_count=len(self.cta.split()),
            ),
        ]
        object.__setattr__(self, "variants", variants)


class GenerationUpdateRequest(BaseModel):
    """Request schema for updating generated content."""

    short_form: Optional[str] = Field(None, description="Updated short-form content")
    long_form: Optional[str] = Field(None, description="Updated long-form content")
    cta: Optional[str] = Field(None, description="Updated CTA content")


class GenerationUpdateResponse(BaseModel):
    """Response schema for content update."""

    message: str = Field(..., description="Success message")
    updated: GenerationResponse = Field(..., description="Updated generation response")


class GenerationAcceptedResponse(BaseModel):
    """Response schema for accepted generation request (202 Accepted)."""

    message: str = Field(..., description="Success message")
    generation_id: UUID = Field(..., description="ID of the generation record")
    status: str = Field(..., description="Current status of the generation (pending, processing, completed, failed)")
