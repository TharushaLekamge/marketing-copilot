"""Security utilities for password hashing and JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any

from bcrypt import checkpw, gensalt, hashpw
from jose import JWTError, jwt

from backend.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password as a string

    Example:
        ```python
        from backend.core.security import hash_password

        hashed = hash_password("my_password")
        ```
    """
    return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise

    Example:
        ```python
        from backend.core.security import verify_password

        is_valid = verify_password("my_password", hashed_password)
        ```
    """
    return checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary containing token payload (typically includes 'sub' for subject/user_id)
        expires_delta: Optional custom expiration time. If not provided, uses default from settings

    Returns:
        Encoded JWT token string

    Example:
        ```python
        from backend.core.security import create_access_token

        token = create_access_token(data={"sub": "user_id"})
        ```
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload as dictionary, or None if token is invalid

    Example:
        ```python
        from backend.core.security import decode_access_token

        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
        ```
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None
