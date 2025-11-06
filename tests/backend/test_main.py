import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the /health endpoint returns the correct response."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert data == {"status": "healthy", "service": "marketing_copilot_backend"}
    assert data["status"] == "healthy"
    assert data["service"] == "marketing_copilot_backend"

