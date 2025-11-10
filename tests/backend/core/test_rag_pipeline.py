"""Unit tests for RAG pipeline module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from backend.core.rag_pipeline import RAGError, RAGOrchestrator, rag_query
from backend.core.semantic_search import SemanticSearchError, SemanticSearchOrchestrator


class TestRAGOrchestrator:
    """Tests for RAGOrchestrator class."""

    @pytest.fixture
    def mock_semantic_search(self):
        """Create a mock semantic search orchestrator."""
        return MagicMock(spec=SemanticSearchOrchestrator)

    @pytest.fixture
    def mock_kernel(self):
        """Create a mock Semantic Kernel instance."""
        kernel = MagicMock()

        # Mock function results
        mock_content = MagicMock()
        mock_content.content = (
            "Based on the provided context, marketing strategies involve careful planning and execution."
        )
        mock_result = MagicMock()
        mock_result.value = [mock_content]

        # Mock invoke
        kernel.invoke = AsyncMock(return_value=mock_result)

        # Mock add_service
        kernel.add_service = MagicMock()

        return kernel

    @pytest.fixture
    def sample_project_id(self) -> UUID:
        """Create a sample project ID."""
        return uuid4()

    @pytest.fixture
    def sample_search_results(self) -> list[dict]:
        """Create sample search results for testing."""
        project_id = uuid4()
        asset_id = uuid4()
        return [
            {
                "text": "This is a document about marketing strategies and campaign planning.",
                "score": 0.85,
                "asset_id": str(asset_id),
                "project_id": str(project_id),
                "chunk_index": 0,
                "metadata": {"source": "marketing_guide.pdf"},
            },
            {
                "text": "Marketing campaigns require careful planning and execution.",
                "score": 0.75,
                "asset_id": str(asset_id),
                "project_id": str(project_id),
                "chunk_index": 1,
                "metadata": {"source": "marketing_guide.pdf", "section": "planning"},
            },
        ]

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    def test__init__creates_orchestrator(self, mock_openai_class, mock_kernel_class, mock_semantic_search, mock_kernel):
        """Test that orchestrator initializes correctly."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)
        assert orchestrator.semantic_search == mock_semantic_search
        assert orchestrator.kernel == mock_kernel
        assert orchestrator.assistant_func is not None

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    def test__init__uses_default_semantic_search(self, mock_openai_class, mock_kernel_class, mock_kernel):
        """Test that orchestrator uses default semantic search when not provided."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        with patch("backend.core.rag_pipeline.SemanticSearchOrchestrator") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            orchestrator = RAGOrchestrator()
            assert orchestrator.semantic_search == mock_instance

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__empty_question__raises_error(self, mock_openai_class, mock_kernel_class, mock_semantic_search, mock_kernel):
        """Test that query raises error for empty question."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        with pytest.raises(RAGError) as exc_info:
            await orchestrator.query(question="", project_id=uuid4())

        assert "Question cannot be empty" in str(exc_info.value)

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__valid_query__retrieves_chunks_and_generates_answer(
        self,
        mock_openai_class,
        mock_kernel_class,
        mock_semantic_search,
        sample_project_id,
        sample_search_results,
        mock_kernel,
    ):
        """Test that query retrieves chunks and generates answer."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        question = "What are marketing strategies?"
        result = await orchestrator.query(question=question, project_id=sample_project_id)

        # Verify semantic search was called
        mock_semantic_search.search_with_context.assert_called_once_with(
            query=question,
            project_id=sample_project_id,
            top_k=5,
            include_metadata=True,
        )

        # Verify kernel was invoked
        mock_kernel.invoke.assert_called_once()

        # Verify result structure
        assert "answer" in result
        assert "citations" in result
        assert "metadata" in result
        assert (
            result["answer"]
            == "Based on the provided context, marketing strategies involve careful planning and execution."
        )
        assert len(result["citations"]) == 2
        assert result["metadata"]["chunks_retrieved"] == 2
        assert result["metadata"]["has_context"] is True

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__no_search_results__generates_answer_without_context(
        self, mock_openai_class, mock_kernel_class, mock_semantic_search, sample_project_id, mock_kernel
    ):
        """Test that query handles no search results gracefully."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=[])

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        question = "What are marketing strategies?"
        result = await orchestrator.query(question=question, project_id=sample_project_id)

        # Verify semantic search was called
        mock_semantic_search.search_with_context.assert_called_once()

        # Verify kernel was invoked (should still generate response)
        mock_kernel.invoke.assert_called_once()

        # Verify result structure
        assert "answer" in result
        assert len(result["citations"]) == 0
        assert result["metadata"]["chunks_retrieved"] == 0
        assert result["metadata"]["has_context"] is False

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__citations_enabled__includes_citations_in_response(
        self,
        mock_openai_class,
        mock_kernel_class,
        mock_semantic_search,
        sample_project_id,
        sample_search_results,
        mock_kernel,
    ):
        """Test that query includes citations when enabled."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        question = "What are marketing strategies?"
        result = await orchestrator.query(question=question, project_id=sample_project_id, include_citations=True)

        assert len(result["citations"]) == 2
        assert result["citations"][0]["index"] == 1
        assert result["citations"][0]["text"] == sample_search_results[0]["text"]
        assert result["citations"][0]["asset_id"] == sample_search_results[0]["asset_id"]

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__citations_disabled__excludes_citations_from_response(
        self,
        mock_openai_class,
        mock_kernel_class,
        mock_semantic_search,
        sample_project_id,
        sample_search_results,
        mock_kernel,
    ):
        """Test that query excludes citations when disabled."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        question = "What are marketing strategies?"
        result = await orchestrator.query(question=question, project_id=sample_project_id, include_citations=False)

        assert len(result["citations"]) == 0

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__custom_top_k__passes_top_k_to_search(
        self,
        mock_openai_class,
        mock_kernel_class,
        mock_semantic_search,
        sample_project_id,
        sample_search_results,
        mock_kernel,
    ):
        """Test that query uses custom top_k parameter."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        question = "What are marketing strategies?"
        await orchestrator.query(question=question, project_id=sample_project_id, top_k=10)

        # Verify semantic search was called with custom top_k
        call_args = mock_semantic_search.search_with_context.call_args
        assert call_args.kwargs["top_k"] == 10

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__semantic_search_error__raises_rag_error(self, mock_openai_class, mock_kernel_class, mock_semantic_search, sample_project_id, mock_kernel):
        """Test that query handles SemanticSearchError."""
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(side_effect=SemanticSearchError("Search failed"))

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        with pytest.raises(RAGError) as exc_info:
            await orchestrator.query(question="test question", project_id=sample_project_id)

        assert "Failed to retrieve context" in str(exc_info.value)

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__empty_llm_response__raises_error(
        self, mock_openai_class, mock_kernel_class, mock_semantic_search, sample_project_id, sample_search_results
    ):
        """Test that query handles empty LLM response."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()

        # Mock empty LLM response
        mock_result = MagicMock()
        mock_result.value = []
        mock_kernel.invoke = AsyncMock(return_value=mock_result)

        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)

        with pytest.raises(RAGError) as exc_info:
            await orchestrator.query(question="test question", project_id=sample_project_id)

        assert "LLM returned empty response" in str(exc_info.value)

    @patch("backend.core.rag_pipeline.Kernel")
    @patch("backend.core.rag_pipeline.OpenAIChatCompletion")
    @pytest.mark.asyncio
    async def test__general_exception__raises_rag_error(
        self, mock_openai_class, mock_kernel_class, mock_semantic_search, sample_project_id, sample_search_results
    ):
        """Test that query handles general exceptions."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel
        mock_openai_class.return_value = MagicMock()
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        orchestrator = RAGOrchestrator(semantic_search_orchestrator=mock_semantic_search)
        mock_kernel.invoke = AsyncMock(side_effect=Exception("Unexpected error"))

        with pytest.raises(RAGError) as exc_info:
            await orchestrator.query(question="test question", project_id=sample_project_id)

        assert "RAG pipeline failed" in str(exc_info.value)


class TestRAGQueryConvenienceFunction:
    """Tests for rag_query convenience function."""

    @pytest.fixture
    def mock_semantic_search(self):
        """Create a mock semantic search orchestrator."""
        return MagicMock(spec=SemanticSearchOrchestrator)

    @pytest.fixture
    def sample_search_results(self) -> list[dict]:
        """Create sample search results."""
        return [
            {
                "text": "Test document content",
                "score": 0.8,
                "asset_id": str(uuid4()),
                "project_id": str(uuid4()),
                "chunk_index": 0,
                "metadata": {"source": "test.pdf"},
            }
        ]

    @pytest.mark.asyncio
    async def test__rag_query__creates_orchestrator_and_queries(self, mock_semantic_search, sample_search_results):
        """Test that convenience function creates orchestrator and queries."""
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        with patch("backend.core.rag_pipeline.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(
                return_value={
                    "answer": "Test answer",
                    "citations": [],
                    "metadata": {"chunks_retrieved": 1, "has_context": True},
                }
            )
            mock_class.return_value = mock_orchestrator

            result = await rag_query(
                question="test question",
                project_id=uuid4(),
                semantic_search_orchestrator=mock_semantic_search,
            )

            assert result["answer"] == "Test answer"
            mock_class.assert_called_once()

    @pytest.mark.asyncio
    async def test__rag_query__passes_all_parameters_to_orchestrator(self, mock_semantic_search, sample_search_results):
        """Test that convenience function passes all parameters."""
        mock_semantic_search.search_with_context = AsyncMock(return_value=sample_search_results)

        with patch("backend.core.rag_pipeline.RAGOrchestrator") as mock_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.query = AsyncMock(
                return_value={
                    "answer": "Test answer",
                    "citations": [],
                    "metadata": {"chunks_retrieved": 1, "has_context": True},
                }
            )
            mock_class.return_value = mock_orchestrator

            project_id = uuid4()
            await rag_query(
                question="test question",
                project_id=project_id,
                top_k=10,
                include_citations=False,
                semantic_search_orchestrator=mock_semantic_search,
            )

            # Verify parameters were passed
            mock_orchestrator.query.assert_called_once_with(
                question="test question",
                project_id=project_id,
                top_k=10,
                include_citations=False,
            )
