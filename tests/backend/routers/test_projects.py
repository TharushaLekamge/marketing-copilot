"""Tests for projects router."""

from backend.models.project import Project
from backend.models.user import User
from fastapi.testclient import TestClient


def test_create_project_success(test_client: TestClient, create_user):
    """Test successful project creation."""
    # Create a user and get token
    user, token = create_user(
        email="projectuser@example.com",
        password="testpassword123",
        name="Project User",
    )

    project_data = {
        "name": "My Marketing Project",
        "description": "A test marketing project",
    }

    response = test_client.post(
        "/api/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Marketing Project"
    assert data["description"] == "A test marketing project"
    assert data["owner_id"] == str(user.id)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_project_without_description(test_client: TestClient, create_user):
    """Test project creation without description."""
    user, token = create_user(
        email="nodesc@example.com",
        password="testpassword123",
        name="No Desc User",
    )

    project_data = {"name": "Simple Project"}

    response = test_client.post(
        "/api/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Simple Project"
    assert data["description"] is None


def test_create_project_unauthorized(test_client: TestClient):
    """Test project creation without authentication returns 401."""
    project_data = {
        "name": "My Project",
        "description": "Test project",
    }

    response = test_client.post("/api/projects", json=project_data)

    assert response.status_code == 403


def test_create_project_invalid_token(test_client: TestClient):
    """Test project creation with invalid token returns 401."""
    project_data = {
        "name": "My Project",
        "description": "Test project",
    }

    response = test_client.post(
        "/api/projects",
        json=project_data,
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401


def test_list_projects_success(test_client: TestClient, create_user, test_db_session):
    """Test listing user's projects."""
    user, token = create_user(
        email="listuser@example.com",
        password="testpassword123",
        name="List User",
    )

    # Create multiple projects for this user
    project1 = Project(
        owner_id=user.id,
        name="Project 1",
        description="First project",
    )
    project2 = Project(
        owner_id=user.id,
        name="Project 2",
        description="Second project",
    )
    test_db_session.add_all([project1, project2])
    test_db_session.commit()

    response = test_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all(project["owner_id"] == str(user.id) for project in data)


def test_list_projects_empty(test_client: TestClient, create_user):
    """Test listing projects when user has none."""
    user, token = create_user(
        email="emptyuser@example.com",
        password="testpassword123",
        name="Empty User",
    )

    response = test_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_projects_other_user_projects_not_included(test_client: TestClient, create_user, test_db_session):
    """Test that users only see their own projects."""
    user1, token1 = create_user(
        email="user1@example.com",
        password="testpassword123",
        name="User 1",
    )
    user2, _ = create_user(
        email="user2@example.com",
        password="testpassword123",
        name="User 2",
    )

    # Create projects for both users
    project1 = Project(owner_id=user1.id, name="User1 Project")
    project2 = Project(owner_id=user2.id, name="User2 Project")
    test_db_session.add_all([project1, project2])
    test_db_session.commit()

    response = test_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {token1}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "User1 Project"
    assert data[0]["owner_id"] == str(user1.id)


def test_get_project_success(test_client: TestClient, create_user, test_db_session):
    """Test getting a specific project."""
    user, token = create_user(
        email="getuser@example.com",
        password="testpassword123",
        name="Get User",
    )

    project = Project(
        owner_id=user.id,
        name="Test Project",
        description="Test description",
    )
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    response = test_client.get(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(project.id)
    assert data["name"] == "Test Project"
    assert data["description"] == "Test description"
    assert data["owner_id"] == str(user.id)


def test_get_project_not_found(test_client: TestClient, create_user):
    """Test getting non-existent project returns 404."""
    user, token = create_user(
        email="notfound@example.com",
        password="testpassword123",
        name="Not Found User",
    )

    response = test_client.get(
        "/api/projects/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_get_project_unauthorized(test_client: TestClient, create_user, test_db_session):
    """Test getting another user's project returns 403."""
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

    response = test_client.get(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this project"


def test_update_project_success(test_client: TestClient, create_user, test_db_session):
    """Test successful project update."""
    user, token = create_user(
        email="updateuser@example.com",
        password="testpassword123",
        name="Update User",
    )

    project = Project(owner_id=user.id, name="Original Name", description="Original desc")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    update_data = {
        "name": "Updated Name",
        "description": "Updated description",
    }

    response = test_client.patch(
        f"/api/projects/{project.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"
    assert data["id"] == str(project.id)


def test_update_project_partial(test_client: TestClient, create_user, test_db_session):
    """Test partial project update (only name)."""
    user, token = create_user(
        email="partial@example.com",
        password="testpassword123",
        name="Partial User",
    )

    project = Project(owner_id=user.id, name="Original", description="Original desc")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    update_data = {"name": "Updated Name"}

    response = test_client.patch(
        f"/api/projects/{project.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Original desc"  # Unchanged


def test_update_project_unauthorized(test_client: TestClient, create_user, test_db_session):
    """Test updating another user's project returns 403."""
    user1, _ = create_user(
        email="owner2@example.com",
        password="testpassword123",
        name="Owner 2",
    )
    user2, token2 = create_user(
        email="other2@example.com",
        password="testpassword123",
        name="Other 2",
    )

    project = Project(owner_id=user1.id, name="Owner's Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    update_data = {"name": "Hacked Name"}

    response = test_client.patch(
        f"/api/projects/{project.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this project"


def test_delete_project_success(test_client: TestClient, create_user, test_db_session):
    """Test successful project deletion."""
    user, token = create_user(
        email="deleteuser@example.com",
        password="testpassword123",
        name="Delete User",
    )

    project = Project(owner_id=user.id, name="To Delete")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)
    project_id = project.id

    response = test_client.delete(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify project was deleted
    deleted_project = test_db_session.query(Project).filter(Project.id == project_id).first()
    assert deleted_project is None


def test_delete_project_unauthorized(test_client: TestClient, create_user, test_db_session):
    """Test deleting another user's project returns 403."""
    user1, _ = create_user(
        email="owner3@example.com",
        password="testpassword123",
        name="Owner 3",
    )
    user2, token2 = create_user(
        email="other3@example.com",
        password="testpassword123",
        name="Other 3",
    )

    project = Project(owner_id=user1.id, name="Owner's Project")
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)

    response = test_client.delete(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this project"


def test_create_project_name_normalization(test_client: TestClient, create_user):
    """Test that project name is normalized (whitespace stripped)."""
    user, token = create_user(
        email="normalize@example.com",
        password="testpassword123",
        name="Normalize User",
    )

    project_data = {
        "name": "  Normalized Project  ",
        "description": "  Normalized Description  ",
    }

    response = test_client.post(
        "/api/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Normalized Project"
    assert data["description"] == "Normalized Description"


def test_get_project_invalid_uuid(test_client: TestClient, create_user):
    """Test getting project with invalid UUID format returns 400."""
    user, token = create_user(
        email="invalid@example.com",
        password="testpassword123",
        name="Invalid User",
    )

    response = test_client.get(
        "/api/projects/invalid-uuid",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Invalid project ID format" in response.json()["detail"]
