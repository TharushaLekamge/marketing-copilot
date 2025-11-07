"""Asset router."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.database import get_db
from backend.models.asset import Asset
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.asset import AssetCreate, AssetResponse, AssetUpdate

router = APIRouter(prefix="/api/projects", tags=["assets"])


@router.post("/{project_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> AssetResponse:
    """Upload a new asset to a project.

    Args:
        project_id: ID of the project to add the asset to
        file: The file to upload
        current_user: The authenticated user
        db: Database session

    Returns:
        AssetResponse: The newly created asset

    Raises:
        HTTPException: If the project is not found or not owned by the user
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Create asset record
    new_asset = Asset(
        id=uuid4(),
        project_id=project_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        ingested=False,
        asset_metadata=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    # TODO: Store the actual file content (S3, local storage, etc.)
    # For now, we only store the metadata

    return AssetResponse.model_validate(new_asset)


@router.get("/{project_id}/assets", response_model=list[AssetResponse])
async def list_assets(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AssetResponse]:
    """List all assets for a project.

    Args:
        project_id: ID of the project
        current_user: The authenticated user
        db: Database session

    Returns:
        list[AssetResponse]: A list of assets

    Raises:
        HTTPException: If the project is not found or not owned by the user
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    assets = db.query(Asset).filter(Asset.project_id == project_id).all()
    return [AssetResponse.model_validate(asset) for asset in assets]


@router.get("/{project_id}/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    project_id: UUID,
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AssetResponse:
    """Get a specific asset by ID.

    Args:
        project_id: ID of the project
        asset_id: ID of the asset
        current_user: The authenticated user
        db: Database session

    Returns:
        AssetResponse: The requested asset

    Raises:
        HTTPException: If the asset or project is not found or not owned by the user
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get asset
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return AssetResponse.model_validate(asset)


@router.patch("/{project_id}/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    project_id: UUID,
    asset_id: UUID,
    asset_data: AssetUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AssetResponse:
    """Update an existing asset.

    Args:
        project_id: ID of the project
        asset_id: ID of the asset to update
        asset_data: New data for the asset
        current_user: The authenticated user
        db: Database session

    Returns:
        AssetResponse: The updated asset

    Raises:
        HTTPException: If the asset or project is not found or not owned by the user
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get asset
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Update fields - handle the metadata -> asset_metadata mapping
    update_data = asset_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "metadata":
            # Map schema field "metadata" to model field "asset_metadata"
            asset.asset_metadata = value
        else:
            setattr(asset, key, value)

    asset.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(asset)

    return AssetResponse.model_validate(asset)


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    project_id: UUID,
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an asset.

    Args:
        project_id: ID of the project
        asset_id: ID of the asset to delete
        current_user: The authenticated user
        db: Database session

    Raises:
        HTTPException: If the asset or project is not found or not owned by the user
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get asset
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # TODO: Delete the actual file from storage (S3, local storage, etc.)
    # For now, we only delete the database record

    db.delete(asset)
    db.commit()
