"""Pytest fixtures for backend tests."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app


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
