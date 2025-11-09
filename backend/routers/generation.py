"""Content generation router."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.generation import GenerationError, generate_content_variants
from backend.database import get_db
from backend.models.asset import Asset
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationUpdateRequest,
    GenerationUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generation"])


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_content(
    generation_request: GenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationResponse:
    """Generate content variants for a marketing campaign.

    Args:
        generation_request: Generation request with project_id, brief, and optional parameters
        current_user: Current authenticated user
        db: Database session

    Returns:
        GenerationResponse: Generated content variants with metadata

    Raises:
        HTTPException: If project not found, user doesn't own project, or generation fails
    """
    # Validate project exists and user owns it
    project = db.query(Project).filter(Project.id == generation_request.project_id).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate content for this project",
        )

    # Get project assets for context
    assets = db.query(Asset).filter(Asset.project_id == generation_request.project_id).all()
    asset_summaries = [
        {
            "filename": asset.filename,
            "content_type": asset.content_type,
            "ingested": asset.ingested,
        }
        for asset in assets
    ]

    # Build prompt from request
    prompt_parts = [f"Brief: {generation_request.brief}"]
    if generation_request.brand_tone:
        prompt_parts.append(f"Brand Tone: {generation_request.brand_tone}")
    if generation_request.audience:
        prompt_parts.append(f"Target Audience: {generation_request.audience}")
    if generation_request.objective:
        prompt_parts.append(f"Objective: {generation_request.objective}")
    if generation_request.channels:
        prompt_parts.append(f"Channels: {', '.join(generation_request.channels)}")
    prompt = "\n".join(prompt_parts)

    try:
        # Generate content variants
        generation_result = await generate_content_variants(
            brief=generation_request.brief,
            project_id=generation_request.project_id,
            project_name=project.name,
            project_description=project.description,
            brand_tone=generation_request.brand_tone,
            asset_summaries=asset_summaries if asset_summaries else None,
        )

        # Extract metadata
        metadata = generation_result.get("metadata", {})
        model = metadata.get("model", "unknown")
        base_url = metadata.get("base_url", "")

        # Create generation record
        generation_record = GenerationRecord(
            project_id=generation_request.project_id,
            user_id=current_user.id,
            prompt=prompt,
            response={
                "short_form": generation_result.get("short_form", ""),
                "long_form": generation_result.get("long_form", ""),
                "cta": generation_result.get("cta", ""),
            },
            model=model,
            tokens=None,  # Token tracking can be added later if needed
        )

        db.add(generation_record)
        db.commit()
        db.refresh(generation_record)

        # Build response
        response = GenerationResponse(
            generation_id=generation_record.id,
            short_form=generation_result.get("short_form", ""),
            long_form=generation_result.get("long_form", ""),
            cta=generation_result.get("cta", ""),
            metadata={
                "model": model,
                "model_info": {"base_url": base_url},
                "project_id": str(generation_request.project_id),
                "tokens_used": None,
                "generation_time": None,
            },
        )

        logger.info(f"Generated content for project {generation_request.project_id} by user {current_user.id}")

        return response
    except GenerationError as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during content generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content generation",
        ) from e


@router.get("/{generation_id}", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def get_generation_record(
    generation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationResponse:
    """Get a single generation record by ID.

    Args:
        generation_id: ID of the generation record to retrieve
        current_user: Current authenticated user
        db: Database session

    Returns:
        GenerationResponse: Generation record with content variants and metadata

    Raises:
        HTTPException: If generation record not found or user doesn't own the project
    """
    # Find the generation record
    generation_record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()

    if generation_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation record not found",
        )

    # Validate project exists and user owns it
    project = db.query(Project).filter(Project.id == generation_record.project_id).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this generation record",
        )

    # Extract response data
    response_data = generation_record.response or {}
    short_form = response_data.get("short_form", "")
    long_form = response_data.get("long_form", "")
    cta = response_data.get("cta", "")

    # Extract token usage information if available
    tokens_used = None
    if generation_record.tokens:
        if isinstance(generation_record.tokens, dict):
            prompt_tokens = generation_record.tokens.get("prompt", 0)
            completion_tokens = generation_record.tokens.get("completion", 0)
            tokens_used = prompt_tokens + completion_tokens
        elif isinstance(generation_record.tokens, int):
            tokens_used = generation_record.tokens

    # Build response
    response = GenerationResponse(
        generation_id=generation_record.id,
        short_form=short_form,
        long_form=long_form,
        cta=cta,
        metadata={
            "model": generation_record.model,
            "model_info": {"base_url": ""},  # Base URL not stored in generation record
            "project_id": str(generation_record.project_id),
            "tokens_used": tokens_used,
            "generation_time": None,  # Generation time not stored in generation record
        },
    )

    logger.info(
        f"Retrieved generation record {generation_id} "
        f"(project {generation_record.project_id}) by user {current_user.id}"
    )

    return response


@router.patch("/{generation_id}", response_model=GenerationUpdateResponse, status_code=status.HTTP_200_OK)
async def update_generated_content(
    generation_id: UUID,
    update_request: GenerationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationUpdateResponse:
    """Update generated content variants.

    Args:
        generation_id: ID of the generation record to update
        update_request: Update request with optional content updates
        current_user: Current authenticated user
        db: Database session

    Returns:
        GenerationUpdateResponse: Success message and updated content

    Raises:
        HTTPException: If generation record not found or user doesn't own the project
    """
    # Find the generation record
    generation_record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()

    if generation_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation record not found",
        )

    # Validate project exists and user owns it
    project = db.query(Project).filter(Project.id == generation_record.project_id).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update content for this project",
        )

    # Update the response field with new content (only update fields that are provided)
    current_response = generation_record.response or {}
    updated_response_data = {
        "short_form": update_request.short_form
        if update_request.short_form is not None
        else current_response.get("short_form", ""),
        "long_form": update_request.long_form
        if update_request.long_form is not None
        else current_response.get("long_form", ""),
        "cta": update_request.cta if update_request.cta is not None else current_response.get("cta", ""),
    }

    # Update the generation record in the database
    generation_record.response = updated_response_data
    db.commit()
    db.refresh(generation_record)

    # Extract token usage information if available
    tokens_used = None
    if generation_record.tokens:
        if isinstance(generation_record.tokens, dict):
            prompt_tokens = generation_record.tokens.get("prompt", 0)
            completion_tokens = generation_record.tokens.get("completion", 0)
            tokens_used = prompt_tokens + completion_tokens
        elif isinstance(generation_record.tokens, int):
            tokens_used = generation_record.tokens

    # Build response with updated content and original metadata
    updated_response = GenerationResponse(
        generation_id=generation_record.id,
        short_form=updated_response_data["short_form"],
        long_form=updated_response_data["long_form"],
        cta=updated_response_data["cta"],
        metadata={
            "model": generation_record.model,
            "model_info": {"base_url": ""},  # Base URL not stored in generation record
            "project_id": str(generation_record.project_id),
            "tokens_used": tokens_used,
            "generation_time": None,  # Generation time not stored in generation record
        },
    )

    logger.info(
        f"Updated content for generation {generation_id} "
        f"(project {generation_record.project_id}) by user {current_user.id}"
    )

    return GenerationUpdateResponse(
        message="Content updated successfully",
        updated=updated_response,
    )
