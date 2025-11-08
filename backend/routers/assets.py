"""Asset router."""

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.file_processing import FileValidationError, validate_file
from backend.core.ingestion import IngestionError, ingest_asset
from backend.core.storage import FileNotFoundError, StorageError, get_storage
from backend.core.vector_store import VectorStoreError, get_vector_store
from backend.database import SessionLocal, get_db
from backend.models.asset import Asset
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.asset import AssetResponse, AssetUpdate, IngestionResponse

logger = logging.getLogger(__name__)

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

    # Validate filename
    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}",
        ) from e

    # Validate file
    try:
        validate_file(file_content, file.filename)
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    # Create asset record
    asset_id = uuid4()
    new_asset = Asset(
        id=asset_id,
        project_id=project_id,
        filename=file.filename.strip(),
        content_type=file.content_type or "application/octet-stream",
        ingested=False,
        ingesting=False,
        asset_metadata=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    # Store file content
    try:
        storage = get_storage()
        storage.save(project_id, asset_id, file.filename.strip(), file_content)
    except StorageError as e:
        # Rollback database transaction
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        ) from e

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


@router.get("/{project_id}/assets/{asset_id}/download")
async def download_asset(
    project_id: UUID,
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Download an asset file.

    Args:
        project_id: ID of the project
        asset_id: ID of the asset
        current_user: The authenticated user
        db: Database session

    Returns:
        Response: File download response with file content

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

    # Read file from storage
    try:
        storage = get_storage()
        file_content = storage.read(project_id, asset_id, asset.filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage",
        )
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}",
        ) from e

    # Return file with appropriate headers
    return Response(
        content=file_content,
        media_type=asset.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{asset.filename}"',
        },
    )


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

    # Check if asset is currently being ingested
    if asset.ingesting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset is currently being ingested and cannot be updated",
        )

    # Update fields - handle the metadata -> asset_metadata mapping
    update_data = asset_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "metadata":
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

    # Check if asset is currently being ingested
    if asset.ingesting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset is currently being ingested and cannot be deleted",
        )

    # Delete vectors from vector store if asset was ingested
    if asset.ingested:
        try:
            vector_store = get_vector_store()
            vector_store.delete_by_asset(asset_id)
        except VectorStoreError:
            # Log error but continue with deletion
            # In production, you might want to handle this differently
            pass

    # Delete file from storage
    try:
        storage = get_storage()
        storage.delete(project_id, asset_id, asset.filename)
    except FileNotFoundError:
        # File doesn't exist in storage, continue with database deletion
        pass
    except StorageError:
        # Log error but continue with database deletion
        # In production, you might want to handle this differently
        pass

    # Delete database record
    db.delete(asset)
    db.commit()


def _ingest_asset_background(asset_id: UUID, project_id: UUID) -> None:
    """Background task wrapper for asset ingestion.

    Creates a new database session for the background task since the original
    session will be closed after the response is sent.

    Args:
        asset_id: ID of the asset to ingest
        project_id: ID of the project the asset belongs to
    """
    db = SessionLocal()
    try:
        ingest_asset(asset_id, project_id, db)
    except IngestionError as e:
        logger.error(f"Background ingestion failed for asset {asset_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in background ingestion for asset {asset_id}: {e}")
    finally:
        db.close()


@router.post(
    "/{project_id}/assets/{asset_id}/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_asset_endpoint(
    project_id: UUID,
    asset_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> IngestionResponse:
    """Start ingestion of an asset.

    This endpoint triggers the ingestion process for an asset in the background.
    The ingestion process includes:
    1. Extracting text from the file
    2. Chunking the text
    3. Generating embeddings
    4. Storing vectors in the vector store

    Args:
        project_id: ID of the project
        asset_id: ID of the asset to ingest
        background_tasks: FastAPI background tasks for async execution
        current_user: The authenticated user
        db: Database session

    Returns:
        IngestionResponse: Confirmation that ingestion has started

    Raises:
        HTTPException: If the asset or project is not found, not owned by the user,
            or if the asset is already being ingested
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

    # Check if asset is already being ingested
    if asset.ingesting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset is already being ingested",
        )

    # Add background task for ingestion
    background_tasks.add_task(_ingest_asset_background, asset_id, project_id)

    logger.info(f"Ingestion started for asset {asset_id} in project {project_id}")

    return IngestionResponse(
        message="Ingestion started",
        asset_id=asset_id,
        ingesting=True,
    )
