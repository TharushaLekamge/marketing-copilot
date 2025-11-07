"""Tests for authentication router."""

import os
from datetime import datetime, timezone

from backend.core.security import decode_access_token, hash_password, verify_password
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


def test_login_success(test_client: TestClient, create_user):
    """Test successful user login."""
    # Create a user directly in the database
    user, _ = create_user(
        email="login@example.com",
        password="testpassword123",
        name="Login User",
    )

    # Login with correct credentials
    login_data = {
        "email": "login@example.com",
        "password": "testpassword123",
    }

    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "user" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0

    # Verify user information
    user_data = data["user"]
    assert user_data["email"] == "login@example.com"
    assert user_data["name"] == "Login User"
    assert user_data["role"] == "user"
    assert user_data["id"] == str(user.id)
    assert "created_at" in user_data

    # Verify token is valid JWT
    token_payload = decode_access_token(data["access_token"])
    assert token_payload is not None
    assert "sub" in token_payload
    assert token_payload["sub"] == str(user.id)
    assert "exp" in token_payload


def test_login_invalid_email(test_client: TestClient):
    """Test login with non-existent email returns 401."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "testpassword123",
    }

    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_invalid_password(test_client: TestClient, create_user):
    """Test login with wrong password returns 401."""
    # Create a user directly in the database
    _, _ = create_user(
        email="login@example.com",
        password="correctpassword123",
        name="Wrong Pass User",
    )

    # Login with wrong password
    login_data = {
        "email": "login@example.com",
        "password": "wrongpassword123",
    }

    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_invalid_email_format(test_client: TestClient):
    """Test login with invalid email format returns 422."""
    login_data = {
        "email": "invalid-email",
        "password": "testpassword123",
    }

    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("email" in str(err).lower() for err in error_detail)


def test_login_missing_fields(test_client: TestClient):
    """Test login with missing required fields returns 422."""
    # Missing email
    response1 = test_client.post("/api/auth/login", json={"password": "testpassword123"})
    assert response1.status_code == 422

    # Missing password
    response2 = test_client.post("/api/auth/login", json={"email": "test@example.com"})
    assert response2.status_code == 422


def test_login_token_contains_user_id(test_client: TestClient, create_user):
    """Test that login token contains correct user ID."""
    # Create a user directly in the database
    user, _ = create_user(
        email="tokenuser@example.com",
        password="testpassword123",
        name="Token User",
    )

    # Login
    login_data = {
        "email": "tokenuser@example.com",
        "password": "testpassword123",
    }
    login_response = test_client.post("/api/auth/login", json=login_data)

    assert login_response.status_code == 200
    data = login_response.json()

    # Decode token and verify user ID
    token_payload = decode_access_token(data["access_token"])
    assert token_payload is not None
    assert token_payload["sub"] == str(user.id)


def test_login_response_structure(test_client: TestClient, create_user):
    """Test that login response has correct structure."""
    # Create a user directly in the database
    _, _ = create_user(
        email="structure@example.com",
        password="testpassword123",
        name="Structure User",
    )

    # Login
    login_data = {
        "email": "structure@example.com",
        "password": "testpassword123",
    }
    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()

    # Verify top-level fields
    assert "access_token" in data
    assert "token_type" in data
    assert "user" in data

    # Verify token fields
    assert isinstance(data["access_token"], str)
    assert data["token_type"] == "bearer"

    # Verify user object structure
    user = data["user"]
    required_fields = ["id", "email", "name", "role", "created_at"]
    for field in required_fields:
        assert field in user, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(user["id"], str)
    assert isinstance(user["email"], str)
    assert isinstance(user["name"], str)
    assert isinstance(user["role"], str)
    assert isinstance(user["created_at"], str)


def test_login_empty_password(test_client: TestClient, create_user):
    """Test login with empty password returns 401."""
    # Create a user directly in the database
    _, _ = create_user(
        email="emptypass@example.com",
        password="testpassword123",
        name="Empty Pass User",
    )

    # Login with empty password
    login_data = {
        "email": "emptypass@example.com",
        "password": "",
    }

    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_token_expiration(test_client: TestClient, create_user):
    """Test that login token has expiration claim."""
    # Create a user directly in the database
    _, _ = create_user(
        email="expire@example.com",
        password="testpassword123",
        name="Expire User",
    )

    # Login
    login_data = {
        "email": "expire@example.com",
        "password": "testpassword123",
    }
    response = test_client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()

    # Decode token and verify expiration
    token_payload = decode_access_token(data["access_token"])
    assert token_payload is not None
    assert "exp" in token_payload
    assert isinstance(token_payload["exp"], (int, float))
