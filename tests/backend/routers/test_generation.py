"""Tests for generation router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.core.generation import GenerationError
from backend.models.asset import Asset
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from fastapi.testclient import TestClient

# TODO: Remove this mock when settings.serve_actual_generation check is removed from generation router
# This mock is needed because the router checks settings.serve_actual_generation before running actual generation


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_success(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test successful content generation."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    # Setup mock generation result
    mock_generate.return_value = {
        "short_form": "Check out our new product! #innovation",
        "long_form": "We're excited to introduce our latest innovation that will revolutionize the way you work...",
        "cta": "Click here to learn more and get started today!",
        "metadata": {
            "model": "gpt-3.5-turbo-instruct",
            "provider": "openai",
            "project_id": None,
        },
    }

    # Create user and project
    user, token = create_user(
        email="genuser@example.com",
        password="testpassword123",
        name="Gen User",
    )

    project = Project(
        owner_id=user.id,
        name="Test Project",
        description="Test project for generation",
    )
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create request
    request_data = {
        "project_id": str(project.id),
        "brief": "Launch a new product campaign",
        "brand_tone": "Professional and friendly",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["short_form"] == "Check out our new product! #innovation"
    assert (
        data["long_form"]
        == "We're excited to introduce our latest innovation that will revolutionize the way you work..."
    )
    assert data["cta"] == "Click here to learn more and get started today!"
    assert data["metadata"]["model"] == "gpt-3.5-turbo-instruct"
    assert data["metadata"]["project_id"] == str(project.id)
    assert "variants" in data

    # Verify generation record was created
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).first()
    assert record is not None
    assert record.user_id == user.id
    assert record.model == "gpt-3.5-turbo-instruct"
    assert "Launch a new product campaign" in record.prompt

    # Verify generate_content_variants was called with correct arguments
    mock_generate.assert_called_once()
    call_args = mock_generate.call_args
    assert call_args[1]["brief"] == "Launch a new product campaign"
    assert call_args[1]["project_id"] == project.id
    assert call_args[1]["project_name"] == "Test Project"
    assert call_args[1]["brand_tone"] == "Professional and friendly"


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_all_optional_fields(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test content generation with all optional fields."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.return_value = {
        "short_form": "Short content",
        "long_form": "Long content",
        "cta": "CTA content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="allfields@example.com",
        password="testpassword123",
        name="All Fields User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
        "brand_tone": "Casual",
        "audience": "Young professionals",
        "objective": "Increase brand awareness",
        "channels": ["social", "email"],
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["short_form"] == "Short content"
    assert data["long_form"] == "Long content"
    assert data["cta"] == "CTA content"

    # Verify all fields were passed to generation
    call_args = mock_generate.call_args
    assert call_args[1]["brief"] == "Campaign brief"
    assert call_args[1]["brand_tone"] == "Casual"


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_assets(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test content generation with project assets."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.return_value = {
        "short_form": "Short content",
        "long_form": "Long content",
        "cta": "CTA content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="assets@example.com",
        password="testpassword123",
        name="Assets User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create assets
    asset1 = Asset(
        project_id=project.id,
        filename="document.pdf",
        content_type="application/pdf",
        ingested=True,
    )
    asset2 = Asset(
        project_id=project.id,
        filename="image.jpg",
        content_type="image/jpeg",
        ingested=False,
    )
    test_db_session.add_all([asset1, asset2])
    test_db_session.commit()

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    # Verify assets were passed to generation
    call_args = mock_generate.call_args
    asset_summaries = call_args[1]["asset_summaries"]
    assert len(asset_summaries) == 2
    assert asset_summaries[0]["filename"] == "document.pdf"
    assert asset_summaries[1]["filename"] == "image.jpg"


def test_generate_content_without_auth(test_client: TestClient):
    """Test content generation without authentication returns 403."""
    request_data = {
        "project_id": str(uuid4()),
        "brief": "Campaign brief",
    }

    response = test_client.post("/api/generate", json=request_data)

    assert response.status_code == 403


def test_generate_content_with_nonexistent_project(test_client: TestClient, create_user):
    """Test content generation with non-existent project returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    request_data = {
        "project_id": str(uuid4()),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_generate_content_with_other_user_project(test_client: TestClient, create_user, test_db_session):
    """Test content generation with another user's project returns 403."""
    user1, _ = create_user(
        email="owner@example.com",
        password="testpassword123",
        name="Owner",
    )
    user2, token2 = create_user(
        email="other@example.com",
        password="testpassword123",
        name="Other User",
    )

    project = Project(owner_id=user1.id, name="Owner's Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to generate content for this project"


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_generation_error(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test content generation when generation fails."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.side_effect = GenerationError("LLM service unavailable")

    user, token = create_user(
        email="error@example.com",
        password="testpassword123",
        name="Error User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert "Content generation failed" in response.json()["detail"]
    assert "LLM service unavailable" in response.json()["detail"]

    # Verify no generation record was created
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).first()
    assert record is None


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_unexpected_error(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test content generation when unexpected error occurs."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.side_effect = Exception("Unexpected database error")

    user, token = create_user(
        email="unexpected@example.com",
        password="testpassword123",
        name="Unexpected User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert "unexpected error" in response.json()["detail"].lower()


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_creates_generation_record(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test that generation record is created with correct data."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.return_value = {
        "short_form": "Short",
        "long_form": "Long",
        "cta": "CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="record@example.com",
        password="testpassword123",
        name="Record User",
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

    assert response.status_code == 201

    # Verify generation record
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).first()
    assert record is not None
    assert record.user_id == user.id
    assert record.project_id == project.id
    assert record.model == "gpt-3.5-turbo-instruct"
    assert record.response["short_form"] == "Short"
    assert record.response["long_form"] == "Long"
    assert record.response["cta"] == "CTA"
    assert "Test brief" in record.prompt
    assert "Professional" in record.prompt


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_minimal_request(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test content generation with minimal required fields only."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.return_value = {
        "short_form": "Short",
        "long_form": "Long",
        "cta": "CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="minimal@example.com",
        password="testpassword123",
        name="Minimal User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "short_form" in data
    assert "long_form" in data
    assert "cta" in data
    assert "metadata" in data
    assert "variants" in data


def test_generate_content_with_invalid_project_id_format(test_client: TestClient, create_user):
    """Test content generation with invalid project ID format."""
    user, token = create_user(
        email="invalid@example.com",
        password="testpassword123",
        name="Invalid User",
    )

    request_data = {
        "project_id": "not-a-uuid",
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # FastAPI will validate UUID format and return 422
    assert response.status_code == 422


def test_generate_content_with_empty_brief(test_client: TestClient, create_user, test_db_session):
    """Test content generation with empty brief returns validation error."""
    user, token = create_user(
        email="empty@example.com",
        password="testpassword123",
        name="Empty User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Pydantic validation should reject empty brief
    assert response.status_code == 422


@patch("backend.routers.generation.settings")
@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_response_includes_variants(
    mock_generate: AsyncMock, mock_settings, test_client: TestClient, create_user, test_db_session
):
    """Test that response includes variants array with calculated statistics."""
    # TODO: Remove this mock when settings.serve_actual_generation check is removed
    mock_settings.serve_actual_generation = True
    
    mock_generate.return_value = {
        "short_form": "Short form content here",
        "long_form": "Long form content with more words here",
        "cta": "CTA content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="variants@example.com",
        password="testpassword123",
        name="Variants User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    request_data = {
        "project_id": str(project.id),
        "brief": "Campaign brief",
    }

    response = test_client.post(
        "/api/generate",
        json=request_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "variants" in data
    assert len(data["variants"]) == 3

    # Check variant structure
    variant_types = [v["variant_type"] for v in data["variants"]]
    assert "short_form" in variant_types
    assert "long_form" in variant_types
    assert "cta" in variant_types

    # Check statistics
    for variant in data["variants"]:
        assert "content" in variant
        assert "character_count" in variant
        assert "word_count" in variant
        assert variant["character_count"] > 0
        assert variant["word_count"] > 0
