"""Tests for generation router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.core.generation import GenerationError
from backend.models.asset import Asset
from backend.models.generation_record import GenerationRecord
from backend.models.project import Project
from fastapi.testclient import TestClient


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_success(mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session):
    """Test successful content generation."""

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
    assert "generation_id" in data
    assert data["generation_id"] is not None
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
    assert str(record.id) == data["generation_id"]
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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_all_optional_fields(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test content generation with all optional fields."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_assets(mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session):
    """Test content generation with project assets."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_generation_error(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test content generation when generation fails."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_unexpected_error(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test content generation when unexpected error occurs."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_creates_generation_record(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test that generation record is created with correct data."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_with_minimal_request(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test content generation with minimal required fields only."""

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


@patch("backend.routers.generation.generate_content_variants")
def test_generate_content_response_includes_variants(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test that response includes variants array with calculated statistics."""

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


# Tests for update_generated_content endpoint


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_success(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test successful content update."""
    # First, create a generation record
    mock_generate.return_value = {
        "short_form": "Original short form",
        "long_form": "Original long form content",
        "cta": "Original CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="updateuser@example.com",
        password="testpassword123",
        name="Update User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the generation record ID
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    generation_id = record.id

    # Now update the content
    update_request = {
        "short_form": "Updated short form",
        "long_form": "Updated long form content",
        "cta": "Updated CTA",
    }

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Content updated successfully"
    assert "generation_id" in data["updated"]
    assert str(generation_id) == data["updated"]["generation_id"]
    assert data["updated"]["short_form"] == "Updated short form"
    assert data["updated"]["long_form"] == "Updated long form content"
    assert data["updated"]["cta"] == "Updated CTA"
    assert data["updated"]["metadata"]["project_id"] == str(project.id)

    # Verify the generation record was updated in the database
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    assert record is not None
    assert record.response["short_form"] == "Updated short form"
    assert record.response["long_form"] == "Updated long form content"
    assert record.response["cta"] == "Updated CTA"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_partial(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test partial content update (only some fields)."""
    mock_generate.return_value = {
        "short_form": "Original short form",
        "long_form": "Original long form content",
        "cta": "Original CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="partialupdate@example.com",
        password="testpassword123",
        name="Partial Update User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the generation record ID
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    generation_id = record.id

    # Update only short_form
    update_request = {
        "short_form": "Only short form updated",
    }

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated"]["short_form"] == "Only short form updated"
    # Other fields should remain unchanged
    assert data["updated"]["long_form"] == "Original long form content"
    assert data["updated"]["cta"] == "Original CTA"

    # Verify in database
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    assert record.response["short_form"] == "Only short form updated"
    assert record.response["long_form"] == "Original long form content"
    assert record.response["cta"] == "Original CTA"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_preserves_metadata(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test that update preserves original metadata."""
    mock_generate.return_value = {
        "short_form": "Original short form",
        "long_form": "Original long form",
        "cta": "Original CTA",
        "metadata": {"model": "gpt-4", "provider": "openai"},
    }

    user, token = create_user(
        email="metadata@example.com",
        password="testpassword123",
        name="Metadata User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the original record
    original_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    original_model = original_record.model
    generation_id = original_record.id

    # Update content
    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # Metadata should be preserved
    assert data["updated"]["metadata"]["model"] == original_model

    # Verify model is still the same in database
    updated_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    assert updated_record.model == original_model


def test_update_generated_content_without_auth(test_client: TestClient):
    """Test content update without authentication returns 403."""
    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(f"/api/generate/{uuid4()}", json=update_request)

    assert response.status_code == 403


def test_update_generated_content_with_nonexistent_generation_id(test_client: TestClient, create_user):
    """Test content update with non-existent generation_id returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{uuid4()}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Generation record not found"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_with_other_user_project(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test content update with another user's project returns 403."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user1, token1 = create_user(
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

    # Generate content for user1's project
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token1}"},
    )

    # Get the generation record ID
    record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).first()
    generation_id = record.id

    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update content for this project"


def test_update_generated_content_with_nonexistent_generation_id_2(test_client: TestClient, create_user):
    """Test content update with non-existent generation_id returns 404."""
    user, token = create_user(
        email="norecord@example.com",
        password="testpassword123",
        name="No Record User",
    )

    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{uuid4()}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Generation record not found"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_with_tokens(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test that update preserves token information if available."""
    mock_generate.return_value = {
        "short_form": "Original short form",
        "long_form": "Original long form",
        "cta": "Original CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="tokens@example.com",
        password="testpassword123",
        name="Tokens User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Manually set tokens on the generation record
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    record.tokens = {"prompt": 100, "completion": 200}
    test_db_session.commit()

    # Get the generation record ID
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    generation_id = record.id

    # Update content
    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # Tokens should be calculated from the stored token data
    assert data["updated"]["metadata"]["tokens_used"] == 300  # 100 + 200


def test_update_generated_content_with_invalid_generation_id_format(test_client: TestClient, create_user):
    """Test content update with invalid generation ID format."""
    user, token = create_user(
        email="invalid@example.com",
        password="testpassword123",
        name="Invalid User",
    )

    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        "/api/generate/not-a-uuid",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # FastAPI will validate UUID format and return 422
    assert response.status_code == 422


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_all_fields_none(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test update with all fields as None preserves existing content."""
    mock_generate.return_value = {
        "short_form": "Original short form",
        "long_form": "Original long form",
        "cta": "Original CTA",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="allnone@example.com",
        password="testpassword123",
        name="All None User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the generation record ID
    record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    generation_id = record.id

    # Update with all None (should preserve existing)
    update_request = {}

    response = test_client.patch(
        f"/api/generate/{generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # All fields should remain unchanged
    assert data["updated"]["short_form"] == "Original short form"
    assert data["updated"]["long_form"] == "Original long form"
    assert data["updated"]["cta"] == "Original CTA"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_latest_record(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test that update modifies the latest generation record when multiple exist."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="latest@example.com",
        password="testpassword123",
        name="Latest User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content twice
    generate_request = {
        "project_id": str(project.id),
        "brief": "First brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    generate_request2 = {
        "project_id": str(project.id),
        "brief": "Second brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request2,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Count records before update
    records_before = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project.id).count()
    assert records_before == 2

    # Get the latest generation record ID
    latest_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    latest_generation_id = latest_record.id

    # Update should only affect the latest record
    update_request = {
        "short_form": "Updated latest",
    }

    response = test_client.patch(
        f"/api/generate/{latest_generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated"]["short_form"] == "Updated latest"

    # Verify only the latest record was updated
    latest_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    assert latest_record.response["short_form"] == "Updated latest"

    # Verify the older record is unchanged
    older_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.asc())
        .first()
    )
    assert older_record.response["short_form"] == "Content"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_with_specific_generation_id(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test updating a specific generation record by ID."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="specific@example.com",
        password="testpassword123",
        name="Specific User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content twice
    generate_request = {
        "project_id": str(project.id),
        "brief": "First brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    generate_request2 = {
        "project_id": str(project.id),
        "brief": "Second brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request2,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the older (first) generation record
    older_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.asc())
        .first()
    )
    older_generation_id = older_record.id

    # Update the older record specifically
    update_request = {
        "short_form": "Updated older record",
    }

    response = test_client.patch(
        f"/api/generate/{older_generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated"]["short_form"] == "Updated older record"

    # Verify the older record was updated
    updated_older_record = (
        test_db_session.query(GenerationRecord).filter(GenerationRecord.id == older_generation_id).first()
    )
    assert updated_older_record.response["short_form"] == "Updated older record"

    # Verify the latest record is unchanged
    latest_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    assert latest_record.response["short_form"] == "Content"


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_with_nonexistent_generation_id(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test updating with a non-existent generation_id returns 404."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="nonexistent@example.com",
        password="testpassword123",
        name="Nonexistent User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content first
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to update with a non-existent generation_id
    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{uuid4()}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "Generation record not found" in response.json()["detail"]


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_with_different_user_project(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test updating with a generation_id from another user's project returns 403."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user1, token1 = create_user(
        email="user1@example.com",
        password="testpassword123",
        name="User 1",
    )
    user2, token2 = create_user(
        email="user2@example.com",
        password="testpassword123",
        name="User 2",
    )

    project1 = Project(owner_id=user1.id, name="User 1 Project")
    test_db_session.add(project1)
    test_db_session.commit()
    test_db_session.refresh(project1)

    # Generate content for user1's project
    generate_request1 = {
        "project_id": str(project1.id),
        "brief": "Project 1 brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request1,
        headers={"Authorization": f"Bearer {token1}"},
    )

    # Get generation_id from project1
    project1_record = test_db_session.query(GenerationRecord).filter(GenerationRecord.project_id == project1.id).first()
    project1_generation_id = project1_record.id

    # Try to update user1's generation using user2's token
    update_request = {
        "short_form": "Updated content",
    }

    response = test_client.patch(
        f"/api/generate/{project1_generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert "Not authorized to update content for this project" in response.json()["detail"]


@patch("backend.routers.generation.generate_content_variants")
def test_update_generated_content_specific_generation_by_id(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test updating a specific generation record by ID."""
    mock_generate.return_value = {
        "short_form": "Content",
        "long_form": "Content",
        "cta": "Content",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="fallback@example.com",
        password="testpassword123",
        name="Fallback User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content twice
    generate_request = {
        "project_id": str(project.id),
        "brief": "First brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    generate_request2 = {
        "project_id": str(project.id),
        "brief": "Second brief",
    }
    test_client.post(
        "/api/generate",
        json=generate_request2,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get the latest generation record ID
    latest_record = (
        test_db_session.query(GenerationRecord)
        .filter(GenerationRecord.project_id == project.id)
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    latest_generation_id = latest_record.id

    # Update the latest record
    update_request = {
        "short_form": "Updated latest",
    }

    response = test_client.patch(
        f"/api/generate/{latest_generation_id}",
        json=update_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated"]["short_form"] == "Updated latest"

    # Verify the latest record was updated
    updated_latest_record = (
        test_db_session.query(GenerationRecord).filter(GenerationRecord.id == latest_generation_id).first()
    )
    assert updated_latest_record.response["short_form"] == "Updated latest"
