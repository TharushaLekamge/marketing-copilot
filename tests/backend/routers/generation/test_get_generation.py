"""Tests for generation router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.models.project import Project
from fastapi.testclient import TestClient


@patch("backend.routers.generation.generate_content_variants")
def test_get_generation_record_success(mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session):
    """Test successful retrieval of a generation record."""
    mock_generate.return_value = {
        "short_form": "Short form content",
        "long_form": "Long form content with more details",
        "cta": "Click here to learn more!",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="getuser@example.com",
        password="testpassword123",
        name="Get User",
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
    generate_response = test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert generate_response.status_code == 201
    generation_id = generate_response.json()["generation_id"]

    # Get the generation record
    response = test_client.get(
        f"/api/generate/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["generation_id"] == generation_id
    assert data["short_form"] == "Short form content"
    assert data["long_form"] == "Long form content with more details"
    assert data["cta"] == "Click here to learn more!"
    assert data["metadata"]["model"] == "gpt-3.5-turbo-instruct"
    assert data["metadata"]["project_id"] == str(project.id)
    assert "variants" in data
    assert len(data["variants"]) == 3


def test_get_generation_record_not_found(test_client: TestClient, create_user):
    """Test getting a non-existent generation record returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    response = test_client.get(
        f"/api/generate/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Generation record not found"


# TODO: To be moved to projects after completion

@patch("backend.routers.generation.generate_content_variants")
def test_list_generation_records_success(
    mock_generate: AsyncMock, test_client: TestClient, create_user, test_db_session
):
    """Test successful retrieval of all generation records for a project."""
    mock_generate.return_value = {
        "short_form": "Short form content",
        "long_form": "Long form content with more details",
        "cta": "Click here to learn more!",
        "metadata": {"model": "gpt-3.5-turbo-instruct", "provider": "openai"},
    }

    user, token = create_user(
        email="listuser@example.com",
        password="testpassword123",
        name="List User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Generate content multiple times
    generate_request = {
        "project_id": str(project.id),
        "brief": "Test brief 1",
    }
    generate_response1 = test_client.post(
        "/api/generate",
        json=generate_request,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert generate_response1.status_code == 201

    generate_request2 = {
        "project_id": str(project.id),
        "brief": "Test brief 2",
    }
    generate_response2 = test_client.post(
        "/api/generate",
        json=generate_request2,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert generate_response2.status_code == 201

    # List all generation records for the project
    response = test_client.get(
        f"/api/projects/{project.id}/generation-records",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Verify all records have the expected structure
    for record in data:
        assert "generation_id" in record
        assert "short_form" in record
        assert "long_form" in record
        assert "cta" in record
        assert "metadata" in record
        assert record["metadata"]["project_id"] == str(project.id)
        assert "variants" in record
        assert len(record["variants"]) == 3

    # Verify records are ordered by created_at desc (newest first)
    generation_ids = [record["generation_id"] for record in data]
    assert generation_ids[0] == generate_response2.json()["generation_id"]
    assert generation_ids[1] == generate_response1.json()["generation_id"]


def test_list_generation_records_project_not_found(test_client: TestClient, create_user):
    """Test listing generation records for a non-existent project returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    response = test_client.get(
        f"/api/projects/{uuid4()}/generation-records",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"