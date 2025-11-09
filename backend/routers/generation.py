"""Content generation router."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.core.dependencies import get_current_user
from backend.core.generation import GenerationError, generate_content_variants
from backend.database import get_db
from backend.models.asset import Asset
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.generation import GenerationRequest, GenerationResponse

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

    # Check if actual generation should be used (controlled by SERVE_ACTUAL_GENERATION env var)
    if settings.serve_actual_generation:
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
    else:
        # Return dummy values for frontend development
        # Build dummy response based on request
        dummy_short_form = f"🚀 {generation_request.brief[:200]}... Get started today!"
        dummy_long_form = f"""Introducing our latest campaign: {generation_request.brief}"""
        dummy_cta = f"Ready to get started? {generation_request.brief[:100]}... Click here to learn more!"

        # Build response with dummy data
        response = GenerationResponse(
            short_form=dummy_short_form,
            long_form=dummy_long_form,
            cta=dummy_cta,
            metadata={
                "model": "dummy-model-v1.0",
                "model_info": {"base_url": "http://localhost:11434"},
                "project_id": str(generation_request.project_id),
                "tokens_used": 150,
                "generation_time": 0.5,
            },
        )

        logger.info(f"Returned dummy content for project {generation_request.project_id} by user {current_user.id}")

        return response
