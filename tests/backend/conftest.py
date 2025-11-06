"""Pytest fixtures for backend tests."""

import os
from datetime import datetime, timezone
from typing import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.security import hash_password
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User


@pytest.fixture(scope="function")
def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
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
        Function that creates a user with given parameters

    Example:
        ```python
        def test_example(create_user):
            user = create_user(
                email="test@example.com",
                password="testpassword123",
                name="Test User"
            )
            assert user.email == "test@example.com"
        ```
    """
    def _create_user(
        email: str,
        password: str,
        name: str,
        role: str = "user",
    ) -> User:
        """Create a user in the database.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            name: User name
            role: User role (default: "user")

        Returns:
            Created User object
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
        return user

    return _create_user
