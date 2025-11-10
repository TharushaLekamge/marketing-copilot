"""Content generation router."""

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.generation import GenerationError, generate_content_variants
from backend.database import SessionLocal, get_db
from backend.models.asset import Asset
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.generation import (
    GenerationAcceptedResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationUpdateRequest,
    GenerationUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generation"])


async def _generate_content_background(
    generation_id: UUID,
    brief: str,
    project_id: UUID,
    project_name: str | None,
    project_description: str | None,
    brand_tone: str | None,
    asset_summaries: list[dict] | None,
    model: str,
) -> None:
    """Background task wrapper for content generation.

    Creates a new database session for the background task since the original
    session will be closed after the response is sent.

    Args:
        generation_id: ID of the generation record
        brief: Campaign brief or description
        project_id: ID of the project
        project_name: Optional project name for context
        project_description: Optional project description for context
        brand_tone: Optional brand tone and style guidelines
        asset_summaries: Optional list of asset summaries for context
        model: Model name to use for generation
    """
    db = SessionLocal()
    try:
        # Update status to processing
        generation_record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
        if not generation_record:
            logger.error(f"Generation record {generation_id} not found in background task")
            return

        generation_record.status = "processing"
        generation_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Generate content variants (async)
        generation_result = await generate_content_variants(
            brief=brief,
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            brand_tone=brand_tone,
            asset_summaries=asset_summaries,
        )

        # Extract metadata
        metadata = generation_result.get("metadata", {})
        tokens = None
        if "tokens" in metadata:
            tokens = metadata["tokens"]

        # Update generation record with results
        generation_record.response = {
            "short_form": generation_result.get("short_form", ""),
            "long_form": generation_result.get("long_form", ""),
            "cta": generation_result.get("cta", ""),
        }
        generation_record.model = metadata.get("model", model)
        generation_record.tokens = tokens
        generation_record.status = "completed"
        generation_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Background generation completed for generation {generation_id}")
    except GenerationError as e:
        logger.error(f"Background generation failed for generation {generation_id}: {e}")
        # Update status to failed
        generation_record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
        if generation_record:
            generation_record.status = "failed"
            generation_record.error_message = str(e)
            generation_record.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.exception(f"Unexpected error in background generation for generation {generation_id}: {e}")
        # Update status to failed
        generation_record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
        if generation_record:
            generation_record.status = "failed"
            generation_record.error_message = f"Unexpected error: {str(e)}"
            generation_record.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("", response_model=GenerationAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_content(
    generation_request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationAcceptedResponse:
    """Generate content variants for a marketing campaign.

    This endpoint accepts the generation request and processes it in the background.
    The generation status can be checked via the GET /api/generate/{generation_id} endpoint.

    Args:
        generation_request: Generation request with project_id, brief, and optional parameters
        background_tasks: FastAPI background tasks for async execution
        current_user: Current authenticated user
        db: Database session

    Returns:
        GenerationAcceptedResponse: Accepted response with generation_id and status

    Raises:
        HTTPException: If project not found or user doesn't own project
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

    # Determine model to use (default from settings)
    from backend.config import settings

    model = settings.openai_chat_model_id or "gpt-4o"

    # Create generation record with pending status
    generation_record = GenerationRecord(
        project_id=generation_request.project_id,
        user_id=current_user.id,
        prompt=prompt,
        response=None,  # Will be populated by background task
        model=model,
        tokens=None,
        status="pending",
    )

    db.add(generation_record)
    db.commit()
    db.refresh(generation_record)

    # Add background task for generation
    background_tasks.add_task(
        _generate_content_background,
        generation_record.id,
        generation_request.brief,
        generation_request.project_id,
        project.name,
        project.description,
        generation_request.brand_tone,
        asset_summaries if asset_summaries else None,
        model,
    )

    logger.info(
        f"Generation request accepted for project {generation_request.project_id} "
        f"by user {current_user.id}, generation_id: {generation_record.id}"
    )

    return GenerationAcceptedResponse(
        message="Generation started",
        generation_id=generation_record.id,
        status="pending",
    )


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

    # Check if generation is still pending or processing
    if generation_record.status in ("pending", "processing"):
        # Return a response indicating the generation is in progress
        # Use empty strings for content fields when not yet completed
        response_data = generation_record.response or {}
        short_form = response_data.get("short_form", "")
        long_form = response_data.get("long_form", "")
        cta = response_data.get("cta", "")

        response = GenerationResponse(
            generation_id=generation_record.id,
            short_form=short_form,
            long_form=long_form,
            cta=cta,
            metadata={
                "model": generation_record.model,
                "model_info": {"base_url": ""},
                "project_id": str(generation_record.project_id),
                "tokens_used": None,
                "generation_time": None,
            },
        )
    elif generation_record.status == "failed":
        # If generation failed, return error information
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=generation_record.error_message or "Content generation failed",
        )
    else:
        # Generation completed - extract response data
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
