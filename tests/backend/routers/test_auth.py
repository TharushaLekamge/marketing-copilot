"""Tests for authentication router."""

import os
from datetime import datetime, timezone

# Set required environment variables before importing backend modules
os.environ.setdefault(
    "DATABASE_URL", "postgresql://marketing_copilot:marketing_copilot_test@localhost:5432/marketing_copilot_test_db"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production")

from backend.core.security import verify_password
from backend.models.user import User
from fastapi.testclient import TestClient


def test_signup_success(test_client: TestClient, test_db_session):
    """Test successful user signup."""
    signup_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["role"] == "user"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data

    # Verify user was created in database
    user = test_db_session.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.role == "user"
    assert verify_password("testpassword123", user.password_hash) is True


def test_signup_duplicate_email(test_client: TestClient, test_db_session):
    """Test signup with duplicate email returns 400."""
    signup_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123",
        "name": "First User",
    }

    # First signup should succeed
    response1 = test_client.post("/api/auth/signup", json=signup_data)
    assert response1.status_code == 201

    # Second signup with same email should fail
    response2 = test_client.post("/api/auth/signup", json=signup_data)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"


def test_signup_invalid_email(test_client: TestClient):
    """Test signup with invalid email format returns 422."""
    signup_data = {
        "email": "invalid-email",
        "password": "testpassword123",
        "name": "Test User",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("email" in str(err).lower() for err in error_detail)


def test_signup_password_too_short(test_client: TestClient):
    """Test signup with password less than 8 characters returns 422."""
    signup_data = {
        "email": "test@example.com",
        "password": "short",
        "name": "Test User",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("password" in str(err).lower() for err in error_detail)
    assert any("8" in str(err) for err in error_detail)


def test_signup_missing_fields(test_client: TestClient):
    """Test signup with missing required fields returns 422."""
    # Missing email
    response1 = test_client.post("/api/auth/signup", json={"password": "testpassword123", "name": "Test User"})
    assert response1.status_code == 422

    # Missing password
    response2 = test_client.post("/api/auth/signup", json={"email": "test@example.com", "name": "Test User"})
    assert response2.status_code == 422

    # Missing name
    response3 = test_client.post("/api/auth/signup", json={"email": "test@example.com", "password": "testpassword123"})
    assert response3.status_code == 422


def test_signup_name_normalization(test_client: TestClient, test_db_session):
    """Test that name is normalized (whitespace stripped) during signup."""
    signup_data = {
        "email": "normalized@example.com",
        "password": "testpassword123",
        "name": "  Test User  ",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"

    # Verify in database
    user = test_db_session.query(User).filter(User.email == "normalized@example.com").first()
    assert user.name == "Test User"


def test_signup_password_minimum_length(test_client: TestClient):
    """Test that password with exactly 8 characters is accepted."""
    signup_data = {
        "email": "minpass@example.com",
        "password": "12345678",  # Exactly 8 characters
        "name": "Test User",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "minpass@example.com"


def test_signup_response_structure(test_client: TestClient):
    """Test that signup response has correct structure."""
    signup_data = {
        "email": "structure@example.com",
        "password": "testpassword123",
        "name": "Test User",
    }

    response = test_client.post("/api/auth/signup", json=signup_data)

    assert response.status_code == 201
    data = response.json()

    # Verify all required fields are present
    required_fields = ["id", "email", "name", "role", "created_at"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(data["id"], str)
    assert isinstance(data["email"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["role"], str)
    assert isinstance(data["created_at"], str)

    # Verify created_at is valid ISO format
    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
