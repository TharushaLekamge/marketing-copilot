"""Tests for security utilities."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password():
    """Test that password hashing works correctly."""
    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed is not None
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt hash format



def test_verify_password_success():
    """Test that password verification succeeds with correct password."""
    password = "test_password_123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_failure():
    """Test that password verification fails with incorrect password."""
    password = "test_password_123"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_create_access_token():
    """Test that access token is created successfully."""
    data = {"sub": "user_id_123"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_custom_expiry():
    """Test that access token is created with custom expiration."""
    data = {"sub": "user_id_123"}
    expires_delta = timedelta(minutes=60)
    token = create_access_token(data, expires_delta=expires_delta)

    assert token is not None
    decoded = decode_access_token(token)
    assert decoded is not None
    assert "sub" in decoded
    assert decoded["sub"] == "user_id_123"
    assert "exp" in decoded


def test_create_access_token_contains_data():
    """Test that access token contains the provided data."""
    data = {"sub": "user_id_123", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == "user_id_123"
    assert decoded["role"] == "admin"


def test_decode_access_token_success():
    """Test that valid access token is decoded successfully."""
    data = {"sub": "user_id_123"}
    token = create_access_token(data)
    decoded = decode_access_token(token)

    assert decoded is not None
    assert isinstance(decoded, dict)
    assert decoded["sub"] == "user_id_123"
    assert "exp" in decoded


def test_decode_access_token_invalid_token():
    """Test that invalid token returns None."""
    invalid_token = "invalid_token_string"
    decoded = decode_access_token(invalid_token)

    assert decoded is None


def test_decode_access_token_expired():
    """Test that expired token returns None."""
    data = {"sub": "user_id_123"}
    # Create token with expiration in the past (negative delta)
    expires_delta = timedelta(seconds=-1)
    token = create_access_token(data, expires_delta=expires_delta)

    # Token should be expired immediately
    decoded = decode_access_token(token)

    assert decoded is None


def test_decode_access_token_wrong_secret():
    """Test that token with wrong secret key returns None."""
    data = {"sub": "user_id_123"}
    token = create_access_token(data)

    # Try to decode with wrong secret
    with patch("backend.core.security.settings") as mock_settings:
        mock_settings.secret_key = "wrong_secret_key"
        mock_settings.algorithm = "HS256"
        decoded = decode_access_token(token)

        assert decoded is None


def test_token_expiration_time():
    """Test that token expiration is set correctly."""
    data = {"sub": "user_id_123"}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta=expires_delta)
    decoded = decode_access_token(token)

    assert decoded is not None
    exp_timestamp = decoded["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    # Expiration should be approximately 30 minutes from now
    time_diff = exp_datetime - now
    assert 29 <= time_diff.total_seconds() / 60 <= 31
