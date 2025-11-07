"""Tests for assets router."""

from backend.models.asset import Asset
from backend.models.project import Project
from backend.models.user import User
from fastapi.testclient import TestClient


def test_create_asset_success(test_client: TestClient, create_user, test_db_session):
    """Test successful asset creation."""
    # Create a user and project
    user, token = create_user(
        email="assetuser@example.com",
        password="testpassword123",
        name="Asset User",
    )

    project = Project(
        owner_id=user.id,
        name="Test Project",
        description="Test project for assets",
    )
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create a mock file
    file_content = b"Mock file content for testing"
    file_data = {"file": ("test-document.pdf", file_content, "application/pdf")}

    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=file_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test-document.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["project_id"] == str(project.id)
    assert data["ingested"] is False
    assert data["asset_metadata"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify asset was created in database
    asset = test_db_session.query(Asset).filter(Asset.filename == "test-document.pdf").first()
    assert asset is not None
    assert asset.filename == "test-document.pdf"
    assert asset.content_type == "application/pdf"
    assert asset.project_id == project.id


def test_create_asset_without_filename(test_client: TestClient, create_user, test_db_session):
    """Test asset creation without filename (should use 'unnamed')."""
    user, token = create_user(
        email="nofilename@example.com",
        password="testpassword123",
        name="No Filename User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create a mock file without filename
    file_content = b"Mock file content"
    file_data = {"file": (None, file_content, "application/octet-stream")}

    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=file_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "unnamed"
    assert data["content_type"] == "application/octet-stream"


def test_create_asset_without_content_type(test_client: TestClient, create_user, test_db_session):
    """Test asset creation without content type (should use default)."""
    user, token = create_user(
        email="nocontenttype@example.com",
        password="testpassword123",
        name="No Content Type User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create a mock file without content type
    file_content = b"Mock file content"
    file_data = {"file": ("test.txt", file_content, None)}

    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=file_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["content_type"] == "application/octet-stream"


def test_create_asset_unauthorized(test_client: TestClient, test_db_session):
    """Test asset creation without authentication returns 403."""
    # Create a user and project without token
    from backend.core.security import hash_password
    from datetime import datetime, timezone
    from uuid import uuid4

    user = User(
        id=uuid4(),
        email="unauth@example.com",
        password_hash=hash_password("testpassword123"),
        name="Unauth User",
        created_at=datetime.now(timezone.utc),
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    file_content = b"Mock file content"
    file_data = {"file": ("test.pdf", file_content, "application/pdf")}

    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=file_data,
    )

    assert response.status_code == 403


def test_create_asset_project_not_found(test_client: TestClient, create_user):
    """Test asset creation with non-existent project returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    file_content = b"Mock file content"
    file_data = {"file": ("test.pdf", file_content, "application/pdf")}

    response = test_client.post(
        "/api/projects/00000000-0000-0000-0000-000000000000/assets",
        files=file_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_create_asset_other_user_project(test_client: TestClient, create_user, test_db_session):
    """Test asset creation in another user's project returns 404."""
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

    file_content = b"Mock file content"
    file_data = {"file": ("test.pdf", file_content, "application/pdf")}

    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=file_data,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_list_assets_success(test_client: TestClient, create_user, test_db_session):
    """Test listing assets for a project."""
    user, token = create_user(
        email="listuser@example.com",
        password="testpassword123",
        name="List User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Create multiple assets
    asset1 = Asset(
        project_id=project.id,
        filename="asset1.pdf",
        content_type="application/pdf",
        ingested=False,
    )
    asset2 = Asset(
        project_id=project.id,
        filename="asset2.jpg",
        content_type="image/jpeg",
        ingested=True,
    )
    test_db_session.add_all([asset1, asset2])
    test_db_session.commit()

    response = test_client.get(
        f"/api/projects/{project.id}/assets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all(asset["project_id"] == str(project.id) for asset in data)
    filenames = [asset["filename"] for asset in data]
    assert "asset1.pdf" in filenames
    assert "asset2.jpg" in filenames


def test_list_assets_empty(test_client: TestClient, create_user, test_db_session):
    """Test listing assets when project has none."""
    user, token = create_user(
        email="emptyassets@example.com",
        password="testpassword123",
        name="Empty Assets User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    response = test_client.get(
        f"/api/projects/{project.id}/assets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_assets_project_not_found(test_client: TestClient, create_user):
    """Test listing assets for non-existent project returns 404."""
    user, token = create_user(
        email="listnotfound@example.com",
        password="testpassword123",
        name="List Not Found User",
    )

    response = test_client.get(
        "/api/projects/00000000-0000-0000-0000-000000000000/assets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_get_asset_success(test_client: TestClient, create_user, test_db_session):
    """Test getting a specific asset."""
    user, token = create_user(
        email="getuser@example.com",
        password="testpassword123",
        name="Get User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    asset = Asset(
        project_id=project.id,
        filename="test-asset.pdf",
        content_type="application/pdf",
        ingested=False,
        asset_metadata={"author": "Test Author"},
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)

    response = test_client.get(
        f"/api/projects/{project.id}/assets/{asset.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(asset.id)
    assert data["filename"] == "test-asset.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["ingested"] is False
    assert data["asset_metadata"] == {"author": "Test Author"}
    assert data["project_id"] == str(project.id)


def test_get_asset_not_found(test_client: TestClient, create_user, test_db_session):
    """Test getting non-existent asset returns 404."""
    user, token = create_user(
        email="getnotfound@example.com",
        password="testpassword123",
        name="Get Not Found User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    response = test_client.get(
        f"/api/projects/{project.id}/assets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_get_asset_project_not_found(test_client: TestClient, create_user):
    """Test getting asset with non-existent project returns 404."""
    user, token = create_user(
        email="getprojectnotfound@example.com",
        password="testpassword123",
        name="Get Project Not Found User",
    )

    response = test_client.get(
        "/api/projects/00000000-0000-0000-0000-000000000000/assets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_update_asset_success(test_client: TestClient, create_user, test_db_session):
    """Test successful asset update."""
    user, token = create_user(
        email="updateuser@example.com",
        password="testpassword123",
        name="Update User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    asset = Asset(
        project_id=project.id,
        filename="original.pdf",
        content_type="application/pdf",
        ingested=False,
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)

    update_data = {
        "filename": "updated.pdf",
        "content_type": "application/pdf",
        "ingested": True,
        "metadata": {"author": "Updated Author", "version": "2.0"},
    }

    response = test_client.patch(
        f"/api/projects/{project.id}/assets/{asset.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "updated.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["ingested"] is True
    assert data["asset_metadata"] == {"author": "Updated Author", "version": "2.0"}
    assert data["id"] == str(asset.id)

    # Verify asset was updated in database
    test_db_session.refresh(asset)
    assert asset.filename == "updated.pdf"
    assert asset.ingested is True
    assert asset.asset_metadata == {"author": "Updated Author", "version": "2.0"}


def test_update_asset_partial(test_client: TestClient, create_user, test_db_session):
    """Test partial asset update (only filename)."""
    user, token = create_user(
        email="partial@example.com",
        password="testpassword123",
        name="Partial User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    asset = Asset(
        project_id=project.id,
        filename="original.pdf",
        content_type="application/pdf",
        ingested=False,
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)

    update_data = {"filename": "updated.pdf"}

    response = test_client.patch(
        f"/api/projects/{project.id}/assets/{asset.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "updated.pdf"
    assert data["content_type"] == "application/pdf"  # Unchanged
    assert data["ingested"] is False  # Unchanged


def test_update_asset_metadata_only(test_client: TestClient, create_user, test_db_session):
    """Test updating only metadata."""
    user, token = create_user(
        email="metadatonly@example.com",
        password="testpassword123",
        name="Metadata Only User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    asset = Asset(
        project_id=project.id,
        filename="test.pdf",
        content_type="application/pdf",
        ingested=False,
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)

    update_data = {"metadata": {"new_field": "new_value"}}

    response = test_client.patch(
        f"/api/projects/{project.id}/assets/{asset.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["asset_metadata"] == {"new_field": "new_value"}
    assert data["filename"] == "test.pdf"  # Unchanged


def test_update_asset_not_found(test_client: TestClient, create_user, test_db_session):
    """Test updating non-existent asset returns 404."""
    user, token = create_user(
        email="updatenotfound@example.com",
        password="testpassword123",
        name="Update Not Found User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    update_data = {"filename": "updated.pdf"}

    response = test_client.patch(
        f"/api/projects/{project.id}/assets/00000000-0000-0000-0000-000000000000",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_update_asset_project_not_found(test_client: TestClient, create_user):
    """Test updating asset with non-existent project returns 404."""
    user, token = create_user(
        email="updateprojectnotfound@example.com",
        password="testpassword123",
        name="Update Project Not Found User",
    )

    update_data = {"filename": "updated.pdf"}

    response = test_client.patch(
        "/api/projects/00000000-0000-0000-0000-000000000000/assets/00000000-0000-0000-0000-000000000000",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_delete_asset_success(test_client: TestClient, create_user, test_db_session):
    """Test successful asset deletion."""
    user, token = create_user(
        email="deleteuser@example.com",
        password="testpassword123",
        name="Delete User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    asset = Asset(
        project_id=project.id,
        filename="to-delete.pdf",
        content_type="application/pdf",
        ingested=False,
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)
    asset_id = asset.id

    response = test_client.delete(
        f"/api/projects/{project.id}/assets/{asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify asset was deleted
    deleted_asset = test_db_session.query(Asset).filter(Asset.id == asset_id).first()
    assert deleted_asset is None


def test_delete_asset_not_found(test_client: TestClient, create_user, test_db_session):
    """Test deleting non-existent asset returns 404."""
    user, token = create_user(
        email="deletenotfound@example.com",
        password="testpassword123",
        name="Delete Not Found User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    response = test_client.delete(
        f"/api/projects/{project.id}/assets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


def test_delete_asset_project_not_found(test_client: TestClient, create_user):
    """Test deleting asset with non-existent project returns 404."""
    user, token = create_user(
        email="deleteprojectnotfound@example.com",
        password="testpassword123",
        name="Delete Project Not Found User",
    )

    response = test_client.delete(
        "/api/projects/00000000-0000-0000-0000-000000000000/assets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_create_asset_different_file_types(test_client: TestClient, create_user, test_db_session):
    """Test creating assets with different file types."""
    user, token = create_user(
        email="filetypes@example.com",
        password="testpassword123",
        name="File Types User",
    )

    project = Project(owner_id=user.id, name="Test Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    # Test PDF
    pdf_content = b"PDF content"
    pdf_data = {"file": ("document.pdf", pdf_content, "application/pdf")}
    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=pdf_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"

    # Test image
    image_content = b"Image content"
    image_data = {"file": ("image.jpg", image_content, "image/jpeg")}
    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=image_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "image/jpeg"

    # Test text
    text_content = b"Text content"
    text_data = {"file": ("document.txt", text_content, "text/plain")}
    response = test_client.post(
        f"/api/projects/{project.id}/assets",
        files=text_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "text/plain"
