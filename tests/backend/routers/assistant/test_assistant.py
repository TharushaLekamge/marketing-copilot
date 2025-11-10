"""Unit tests for assistant router."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.core.rag_pipeline import RAGError, RAGOrchestrator
from backend.models.project import Project
from backend.models.user import User


class TestQueryAssistant:
    """Tests for POST /api/assistant/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_assistant_success(self, test_client: TestClient, create_user, test_db_session):
        """Test successful assistant query."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        # Create project
        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        # Mock RAG orchestrator
        mock_result = {
            "answer": "Based on the provided context, marketing strategies involve careful planning.",
            "citations": [
                {
                    "index": 1,
                    "text": "Marketing campaigns require careful planning.",
                    "asset_id": str(uuid4()),
                    "chunk_index": 0,
                    "score": 0.85,
                    "metadata": {"source": "test.pdf"},
                }
            ],
            "metadata": {
                "model": "gpt-4o",
                "provider": "openai",
                "project_id": str(project.id),
                "chunks_retrieved": 1,
                "has_context": True,
            },
        }

        with patch("backend.routers.assistant.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(return_value=mock_result)
            mock_class.return_value = mock_orchestrator

            response = test_client.post(
                "/api/assistant/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "project_id": str(project.id),
                    "question": "What are marketing strategies?",
                    "top_k": 5,
                    "include_citations": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "citations" in data
            assert "metadata" in data
            assert data["answer"] == mock_result["answer"]
            assert len(data["citations"]) == 1
            assert data["metadata"]["chunks_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_query_assistant_project_not_found(self, test_client: TestClient, create_user):
        """Test assistant query with non-existent project."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        response = test_client.post(
            "/api/assistant/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(uuid4()),
                "question": "What are marketing strategies?",
            },
        )

        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_query_assistant_unauthorized_project(self, test_client: TestClient, create_user, test_db_session):
        """Test assistant query with unauthorized project."""
        user1, token1 = create_user(
            email="user1@example.com",
            password="testpassword123",
            name="User 1",
        )

        user2, token2 = create_user(
            email="user2@example.com",
            password="testpassword123",
            name="User 2",
        )

        # Create project owned by user1
        project = Project(
            id=uuid4(),
            owner_id=user1.id,
            name="User 1 Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        # Try to query with user2's token
        response = test_client.post(
            "/api/assistant/query",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "project_id": str(project.id),
                "question": "What are marketing strategies?",
            },
        )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_query_assistant_requires_authentication(self, test_client: TestClient, create_user, test_db_session):
        """Test that assistant query requires authentication."""
        user, _ = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()

        response = test_client.post(
            "/api/assistant/query",
            json={
                "project_id": str(project.id),
                "question": "What are marketing strategies?",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_query_assistant_handles_rag_error(self, test_client: TestClient, create_user, test_db_session):
        """Test that assistant query handles RAG errors."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        # Mock RAG orchestrator to raise error
        with patch("backend.routers.assistant.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(side_effect=RAGError("RAG pipeline failed"))
            mock_class.return_value = mock_orchestrator

            response = test_client.post(
                "/api/assistant/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "project_id": str(project.id),
                    "question": "What are marketing strategies?",
                },
            )

            assert response.status_code == 500
            assert "Failed to process query" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_query_assistant_handles_general_exception(
        self, test_client: TestClient, create_user, test_db_session
    ):
        """Test that assistant query handles general exceptions."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        # Mock RAG orchestrator to raise unexpected error
        with patch("backend.routers.assistant.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_class.return_value = mock_orchestrator

            response = test_client.post(
                "/api/assistant/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "project_id": str(project.id),
                    "question": "What are marketing strategies?",
                },
            )

            assert response.status_code == 500
            assert "An unexpected error occurred" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_query_assistant_validates_request(self, test_client: TestClient, create_user):
        """Test that assistant query validates request schema."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        # Missing question
        response = test_client.post(
            "/api/assistant/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(uuid4()),
            },
        )

        assert response.status_code == 422

        # Empty question
        response = test_client.post(
            "/api/assistant/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(uuid4()),
                "question": "",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_assistant_with_custom_top_k(self, test_client: TestClient, create_user, test_db_session):
        """Test assistant query with custom top_k parameter."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        mock_result = {
            "answer": "Test answer",
            "citations": [],
            "metadata": {
                "model": "gpt-4o",
                "provider": "openai",
                "project_id": str(project.id),
                "chunks_retrieved": 3,
                "has_context": True,
            },
        }

        with patch("backend.routers.assistant.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(return_value=mock_result)
            mock_class.return_value = mock_orchestrator

            response = test_client.post(
                "/api/assistant/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "project_id": str(project.id),
                    "question": "What are marketing strategies?",
                    "top_k": 10,
                },
            )

            assert response.status_code == 200
            # Verify top_k was passed to orchestrator
            call_args = mock_orchestrator.query.call_args
            assert call_args.kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_query_assistant_without_citations(self, test_client: TestClient, create_user, test_db_session):
        """Test assistant query without citations."""
        user, token = create_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
        )

        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name="Test Project",
            description="Test Description",
        )
        test_db_session.add(project)
        test_db_session.commit()
        test_db_session.refresh(project)

        mock_result = {
            "answer": "Test answer",
            "citations": [],
            "metadata": {
                "model": "gpt-4o",
                "provider": "openai",
                "project_id": str(project.id),
                "chunks_retrieved": 1,
                "has_context": True,
            },
        }

        with patch("backend.routers.assistant.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(return_value=mock_result)
            mock_class.return_value = mock_orchestrator

            response = test_client.post(
                "/api/assistant/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "project_id": str(project.id),
                    "question": "What are marketing strategies?",
                    "include_citations": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["citations"]) == 0
            # Verify include_citations was passed to orchestrator
            call_args = mock_orchestrator.query.call_args
            assert call_args.kwargs["include_citations"] is False
