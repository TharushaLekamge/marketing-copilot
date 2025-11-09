"""Projects router."""

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database import get_db
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.generation import GenerationResponse
from backend.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    """Create a new project.

    Args:
        project_data: Project creation data (name, description)
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectResponse: Created project information
    """
    new_project = Project(
        id=uuid4(),
        owner_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return ProjectResponse(
        id=str(new_project.id),
        owner_id=str(new_project.owner_id),
        name=new_project.name,
        description=new_project.description,
        created_at=new_project.created_at.isoformat(),
        updated_at=new_project.updated_at.isoformat(),
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectResponse]:
    """List all projects for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of ProjectResponse: User's projects
    """
    projects = db.query(Project).filter(Project.owner_id == current_user.id).all()

    return [
        ProjectResponse(
            id=str(project.id),
            owner_id=str(project.owner_id),
            name=project.name,
            description=project.description,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )
        for project in projects
    ]


@router.get("/{project_id}/generation-records", response_model=list[GenerationResponse], status_code=status.HTTP_200_OK)
async def list_generation_records(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GenerationResponse]:
    """Get all generation records for a project.

    Args:
        project_id: ID of the project
        current_user: Current authenticated user
        db: Database session

    Returns:
        list[GenerationResponse]: List of generation records with content variants and metadata

    Raises:
        HTTPException: If project not found or user doesn't own the project
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    # Validate project exists and user owns it
    project = db.query(Project).filter(Project.id == project_uuid).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access generation records for this project",
        )

    # Get all generation records for the project
    generation_records = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project_uuid)
        .order_by(GenerationRecord.created_at.desc())
        .all()
    )

    # Build response list
    responses = []
    for generation_record in generation_records:
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
        responses.append(response)

    logger.info(f"Retrieved {len(responses)} generation records for project {project_uuid} by user {current_user.id}")

    return responses


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    """Get a specific project by ID.

    Args:
        project_id: Project UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectResponse: Project information

    Raises:
        HTTPException: If project not found or user doesn't have access
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    project = db.query(Project).filter(Project.id == project_uuid).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )

    return ProjectResponse(
        id=str(project.id),
        owner_id=str(project.owner_id),
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    """Update a project.

    Args:
        project_id: Project UUID
        project_data: Project update data (name, description)
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectResponse: Updated project information

    Raises:
        HTTPException: If project not found or user doesn't have access
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    project = db.query(Project).filter(Project.id == project_uuid).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this project",
        )

    # Update fields if provided
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description

    project.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        owner_id=str(project.owner_id),
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a project.

    Args:
        project_id: Project UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If project not found or user doesn't have access
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    project = db.query(Project).filter(Project.id == project_uuid).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project",
        )

    db.delete(project)
    db.commit()
