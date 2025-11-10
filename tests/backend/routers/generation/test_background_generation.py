"""Tests for background generation functionality."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.core.generation import GenerationError
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from fastapi.testclient import TestClient


@patch("backend.routers.generation._generate_content_background")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_returns_202_accepted(
    mock_generate: AsyncMock,
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test that POST /api/generate returns 202 Accepted immediately."""
    user, token = create_user(
        email="asyncuser@example.com",
        password="testpassword123",
        name="Async User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should return 202 Accepted, not 201 Created
    assert response.status_code == 202
    data = response.json()
    assert "message" in data
    assert "generation_id" in data
    assert "status" in data
    assert data["status"] == "pending"
    assert data["message"] == "Generation started"

    # Verify generation record was created with pending status
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).first()
    assert record is not None
    assert record.status == "pending"
    assert record.response is None  # Response not yet populated


@patch("backend.routers.generation._generate_content_background")
def test_generate_content_creates_pending_record(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test that generation record is created with pending status."""
    user, token = create_user(
        email="pending@example.com",
        password="testpassword123",
        name="Pending User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
        "brand_tone": "Professional",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Verify record in database
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    assert record is not None
    assert record.status == "pending"
    assert record.user_id == user.id
    assert record.project_id == project.id
    assert record.response is None
    assert "Test brief" in record.prompt
    assert "Professional" in record.prompt

    # Verify background task was added
    assert mock_background.called


@patch("backend.routers.generation._generate_content_background")
def test_get_generation_record_pending_status(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test GET endpoint returns empty content for pending generation."""
    user, token = create_user(
        email="pendingget@example.com",
        password="testpassword123",
        name="Pending Get User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation request
    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Get the generation record while still pending
    get_response = test_client.get(
        f"/api/generate/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["generation_id"] == generation_id
    # Content should be empty strings for pending status
    assert data["short_form"] == ""
    assert data["long_form"] == ""
    assert data["cta"] == ""


@patch("backend.routers.generation._generate_content_background")
def test_get_generation_record_processing_status(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test GET endpoint handles processing status."""
    user, token = create_user(
        email="processing@example.com",
        password="testpassword123",
        name="Processing User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation request
    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Manually set status to processing
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    record.status = "processing"
    record.updated_at = datetime.now(timezone.utc)
    test_db_session.commit()

    # Get the generation record while processing
    get_response = test_client.get(
        f"/api/generate/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["generation_id"] == generation_id
    # Content should be empty strings for processing status
    assert data["short_form"] == ""
    assert data["long_form"] == ""
    assert data["cta"] == ""


@patch("backend.routers.generation._generate_content_background")
def test_get_generation_record_failed_status(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test GET endpoint returns error for failed generation."""
    user, token = create_user(
        email="failed@example.com",
        password="testpassword123",
        name="Failed User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation request
    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Manually set status to failed
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    record.status = "failed"
    record.error_message = "Generation failed: LLM service unavailable"
    record.updated_at = datetime.now(timezone.utc)
    test_db_session.commit()

    # Get the generation record with failed status
    get_response = test_client.get(
        f"/api/generate/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 500
    assert "Generation failed" in get_response.json()["detail"]
    assert "LLM service unavailable" in get_response.json()["detail"]


@patch("backend.routers.generation._generate_content_background")
def test_get_generation_record_completed_status(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test GET endpoint returns content for completed generation."""
    user, token = create_user(
        email="completed@example.com",
        password="testpassword123",
        name="Completed User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation request
    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Manually set status to completed with content
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    record.status = "completed"
    record.response = {
        "short_form": "Short form content",
        "long_form": "Long form content",
        "cta": "CTA content",
    }
    record.tokens = {"prompt": 100, "completion": 200}
    record.updated_at = datetime.now(timezone.utc)
    test_db_session.commit()

    # Get the generation record with completed status
    get_response = test_client.get(
        f"/api/generate/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["generation_id"] == generation_id
    assert data["short_form"] == "Short form content"
    assert data["long_form"] == "Long form content"
    assert data["cta"] == "CTA content"
    assert data["metadata"]["tokens_used"] == 300  # 100 + 200


async def test_background_task_success():
    """Test background task successfully completes generation."""
    from backend.database import SessionLocal
    from backend.routers.generation import _generate_content_background

    # This test would require a more complex setup with actual database
    # For now, we'll test the logic through integration tests
    pass


@patch("backend.routers.generation.generate_content_variants")
async def test_background_task_updates_status_to_processing(
    mock_generate: AsyncMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test that background task updates status to processing."""
    from backend.database import SessionLocal
    from backend.routers.generation import _generate_content_background

    mock_generate.return_value = {
        "short_form": "Short",
        "long_form": "Long",
        "cta": "CTA",
        "metadata": {"model": "gpt-4o", "provider": "openai"},
    }

    user, token = create_user(
        email="background@example.com",
        password="testpassword123",
        name="Background User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation record manually
    generation_record = GenerationRecord(
        project_id=project.id,
        user_id=user.id,
        prompt="Test brief",
        response=None,
        model="gpt-4o",
        tokens=None,
        status="pending",
    )
    test_db_session.add(generation_record)
    test_db_session.commit()
    test_db_session.refresh(generation_record)

    # Run background task
    await _generate_content_background(
        generation_record.id,
        "Test brief",
        project.id,
        project.name,
        project.description,
        None,
        None,
        "gpt-4o",
    )

    # Refresh record from database
    test_db_session.refresh(generation_record)

    # Status should be completed
    assert generation_record.status == "completed"
    assert generation_record.response is not None
    assert generation_record.response["short_form"] == "Short"
    assert generation_record.response["long_form"] == "Long"
    assert generation_record.response["cta"] == "CTA"


@patch("backend.routers.generation.generate_content_variants")
async def test_background_task_handles_generation_error(
    mock_generate: AsyncMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test that background task handles generation errors correctly."""
    from backend.routers.generation import _generate_content_background

    mock_generate.side_effect = GenerationError("LLM service unavailable")

    user, token = create_user(
        email="errorbg@example.com",
        password="testpassword123",
        name="Error Background User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create generation record manually
    generation_record = GenerationRecord(
        project_id=project.id,
        user_id=user.id,
        prompt="Test brief",
        response=None,
        model="gpt-4o",
        tokens=None,
        status="pending",
    )
    test_db_session.add(generation_record)
    test_db_session.commit()
    test_db_session.refresh(generation_record)

    # Run background task
    await _generate_content_background(
        generation_record.id,
        "Test brief",
        project.id,
        project.name,
        project.description,
        None,
        None,
        "gpt-4o",
    )

    # Refresh record from database
    test_db_session.refresh(generation_record)

    # Status should be failed
    assert generation_record.status == "failed"
    assert generation_record.error_message == "LLM service unavailable"
    assert generation_record.response is None


@patch("backend.routers.generation._generate_content_background")
def test_generate_content_with_background_task_parameters(
    mock_background: MagicMock,
    test_client: TestClient,
    create_user,
    test_db_session,
):
    """Test that background task is called with correct parameters."""
    user, token = create_user(
        email="params@example.com",
        password="testpassword123",
        name="Params User",
    )

    project = Project(owner_id=user.id, name="Test Project", description="Test description")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Test brief",
        "brand_tone": "Professional",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    generation_id = response.json()["generation_id"]

    # Verify background task was called with correct parameters
    assert mock_background.called
    call_args = mock_background.call_args
    assert call_args[0][0] == generation_id  # generation_id
    assert call_args[0][1] == "Test brief"  # brief
    assert call_args[0][2] == project.id  # project_id
    assert call_args[0][3] == "Test Project"  # project_name
    assert call_args[0][4] == "Test description"  # project_description
    assert call_args[0][5] == "Professional"  # brand_tone
