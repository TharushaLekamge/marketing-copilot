"""Projects router."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database import get_db
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

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
