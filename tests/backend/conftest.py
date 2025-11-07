"""Pytest fixtures for backend tests."""

import os
from datetime import datetime, timezone
from typing import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set required environment variables before importing backend modules
# Default test database URL - can be overridden via TEST_DATABASE_URL env var
default_test_db_url = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://marketing_copilot:marketing_copilot_dev@localhost:5432/marketing_copilot_db",
)
os.environ.setdefault("DATABASE_URL", default_test_db_url)
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production"
)

from backend.core.security import create_access_token, hash_password
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a PostgreSQL database engine for testing."""
    # Get test database URL from environment
    # Prefer TEST_DATABASE_URL, fallback to DATABASE_URL, then default
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://marketing_copilot:marketing_copilot_dev@localhost:5432/marketing_copilot_db",
        ),
    )

    # Create engine with connection pooling
    engine = create_engine(
        test_db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup: drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing with automatic rollback."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine,
    )

    # Create session - it will manage its own transaction
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        # Rollback any uncommitted changes to clean up test data
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def test_client(test_db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""

    def override_get_db() -> Generator[Session, None, None]:
        """Override get_db dependency to use test database session."""
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def create_user(test_db_session: Session) -> Callable:
    """Factory function to create users directly in the database.

    Args:
        test_db_session: Database session fixture

    Returns:
        Function that creates a user with given parameters and returns (user, token)

    Example:
        ```python
        def test_example(create_user):
            user, token = create_user(
                email="test@example.com",
                password="testpassword123",
                name="Test User"
            )
            assert user.email == "test@example.com"
            # Use token for authenticated requests
        ```
    """

    def _create_user(
        email: str,
        password: str,
        name: str,
        role: str = "user",
    ) -> tuple[User, str]:
        """Create a user in the database and return user with access token.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            name: User name
            role: User role (default: "user")

        Returns:
            Tuple of (Created User object, JWT access token)
        """
        hashed_password = hash_password(password)
        user = User(
            id=uuid4(),
            email=email,
            name=name,
            password_hash=hashed_password,
            role=role,
            created_at=datetime.now(timezone.utc),
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Create access token for the user
        token = create_access_token(data={"sub": str(user.id)})

        return user, token

    return _create_user
