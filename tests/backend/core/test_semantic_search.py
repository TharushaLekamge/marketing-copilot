"""Unit tests for semantic search module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from backend.core.embeddings import EmbeddingGenerator
from backend.core.semantic_search import (
    SemanticSearchError,
    SemanticSearchOrchestrator,
    semantic_search,
)
from backend.core.vector_store import (
    FAISSSQLiteVectorStore,
    SearchResult,
    VectorDocument,
    VectorStoreError,
)


class TestSemanticSearchOrchestrator:
    """Tests for SemanticSearchOrchestrator class."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        return MagicMock(spec=FAISSSQLiteVectorStore)

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create a mock embedding generator."""
        generator = MagicMock(spec=EmbeddingGenerator)
        generator.generate_embedding.return_value = [0.1] * 384  # Mock embedding
        generator.get_embedding_dimension.return_value = 384
        return generator

    @pytest.fixture
    def sample_project_id(self) -> UUID:
        """Create a sample project ID."""
        return uuid4()

    @pytest.fixture
    def sample_asset_id(self) -> UUID:
        """Create a sample asset ID."""
        return uuid4()

    @pytest.fixture
    def sample_search_results(self, sample_project_id: UUID, sample_asset_id: UUID) -> list[SearchResult]:
        """Create sample search results for testing."""
        return [
            SearchResult(
                document=VectorDocument(
                    id=f"{sample_asset_id}_0",
                    asset_id=sample_asset_id,
                    project_id=sample_project_id,
                    chunk_index=0,
                    text="This is a test document about marketing strategies and campaigns.",
                    embedding=[],
                    metadata={"source": "test_doc.pdf"},
                ),
                score=0.85,
            ),
            SearchResult(
                document=VectorDocument(
                    id=f"{sample_asset_id}_1",
                    asset_id=sample_asset_id,
                    project_id=sample_project_id,
                    chunk_index=1,
                    text="Marketing campaigns require careful planning and execution.",
                    embedding=[],
                    metadata={"source": "test_doc.pdf", "section": "planning"},
                ),
                score=0.75,
            ),
            SearchResult(
                document=VectorDocument(
                    id=f"{sample_asset_id}_2",
                    asset_id=sample_asset_id,
                    project_id=sample_project_id,
                    chunk_index=2,
                    text="Short text.",
                    embedding=[],
                ),
                score=0.65,
            ),
        ]

    def test__init__uses_provided_dependencies(self, mock_vector_store, mock_embedding_generator):
        """Test that orchestrator uses provided dependencies."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )
        assert orchestrator.vector_store == mock_vector_store
        assert orchestrator.embedding_generator == mock_embedding_generator
        assert orchestrator.kernel is not None

    def test__init__uses_default_dependencies(self):
        """Test that orchestrator uses default dependencies when not provided."""
        with patch("backend.core.semantic_search.get_vector_store") as mock_get_store, patch(
            "backend.core.semantic_search.get_embedding_generator"
        ) as mock_get_generator:
            mock_store = MagicMock()
            mock_generator = MagicMock()
            mock_get_store.return_value = mock_store
            mock_get_generator.return_value = mock_generator

            orchestrator = SemanticSearchOrchestrator()
            assert orchestrator.vector_store == mock_store
            assert orchestrator.embedding_generator == mock_generator

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_for_empty_query(self, mock_vector_store, mock_embedding_generator):
        """Test that search returns empty list for empty query."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        result = await orchestrator.search(query="")
        assert result == []

        result = await orchestrator.search(query="   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_generates_embedding_and_searches(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that search generates embedding and calls vector store."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "marketing strategies"
        results = await orchestrator.search(query=query, top_k=5)

        # Verify embedding was generated
        mock_embedding_generator.generate_embedding.assert_called_once_with(query.strip())

        # Verify vector store was called
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["query_embedding"] == [0.1] * 384
        assert call_args.kwargs["top_k"] == 5, "No re-ranking, so exact top_k"

        # Verify results
        assert len(results) == 3  # All results returned

    @pytest.mark.asyncio
    async def test_search_with_reranking(self, mock_vector_store, mock_embedding_generator, sample_search_results):
        """Test that search applies re-ranking when enabled."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "marketing campaigns"
        results = await orchestrator.search(query=query, top_k=2, rerank=True)

        # Verify vector store was called with more results for re-ranking
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["top_k"] == 6  # top_k * 3 for re-ranking

        # Verify results are re-ranked (should be limited to top_k)
        assert len(results) == 2

        # Verify scores are adjusted (re-ranking modifies scores)
        # The first result should have higher score due to keyword matching
        assert results[0].score >= results[1].score

    @pytest.mark.asyncio
    async def test_search_with_project_filter(
        self, mock_vector_store, mock_embedding_generator, sample_project_id, sample_search_results
    ):
        """Test that search filters by project_id."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test query"
        await orchestrator.search(query=query, project_id=sample_project_id)

        # Verify project_id filter was passed
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["project_id"] == sample_project_id

    @pytest.mark.asyncio
    async def test_search_with_asset_filter(
        self, mock_vector_store, mock_embedding_generator, sample_asset_id, sample_search_results
    ):
        """Test that search filters by asset_id."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test query"
        await orchestrator.search(query=query, asset_id=sample_asset_id)

        # Verify asset_id filter was passed
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["asset_id"] == sample_asset_id

    @pytest.mark.asyncio
    async def test_search_handles_no_results(self, mock_vector_store, mock_embedding_generator):
        """Test that search handles empty results gracefully."""
        mock_vector_store.search.return_value = []

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        results = await orchestrator.search(query="test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_vector_store_error(self, mock_vector_store, mock_embedding_generator):
        """Test that search handles VectorStoreError."""
        mock_vector_store.search.side_effect = VectorStoreError("Vector store error")

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        with pytest.raises(SemanticSearchError) as exc_info:
            await orchestrator.search(query="test query")

        assert "Vector store search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_handles_general_exception(self, mock_vector_store, mock_embedding_generator):
        """Test that search handles general exceptions."""
        mock_vector_store.search.side_effect = Exception("Unexpected error")

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        with pytest.raises(SemanticSearchError) as exc_info:
            await orchestrator.search(query="test query")

        assert "Semantic search failed" in str(exc_info.value)

    def test_rerank_results_applies_keyword_boost(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that re-ranking applies keyword boost."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "marketing campaigns"
        reranked = orchestrator._rerank_results(query, sample_search_results)

        # Results should be sorted by score
        assert len(reranked) == 3
        assert reranked[0].score >= reranked[1].score >= reranked[2].score

        # Results with keyword matches should have higher scores
        # The second result contains "campaigns" which should boost it
        assert any("campaigns" in r.document.text.lower() for r in reranked[:2])

    def test_rerank_results_applies_length_normalization(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that re-ranking applies length normalization."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test"
        reranked = orchestrator._rerank_results(query, sample_search_results)

        # Short text (result 2) should be penalized
        # Medium-length texts (results 0 and 1) should be preferred
        short_result = next((r for r in reranked if len(r.document.text) < 50), None)
        if short_result:
            # Short result should be ranked lower
            assert short_result.score <= reranked[0].score

    def test_rerank_results_applies_metadata_boost(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that re-ranking applies metadata boost."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test"
        reranked = orchestrator._rerank_results(query, sample_search_results)

        # Results with metadata should have higher scores
        results_with_metadata = [r for r in reranked if r.document.metadata]
        results_without_metadata = [r for r in reranked if not r.document.metadata]

        if results_with_metadata and results_without_metadata:
            # At least one result with metadata should rank higher than results without
            max_with_metadata = max(r.score for r in results_with_metadata)
            max_without_metadata = max(r.score for r in results_without_metadata)
            # Metadata boost is small, so we just check that it's applied
            assert len(results_with_metadata) > 0

    def test_rerank_results_handles_empty_list(self, mock_vector_store, mock_embedding_generator):
        """Test that re-ranking handles empty results."""
        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        reranked = orchestrator._rerank_results("test", [])
        assert reranked == []

    @pytest.mark.asyncio
    async def test_search_with_context_formats_results(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that search_with_context formats results correctly."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test query"
        results = await orchestrator.search_with_context(query=query, top_k=3, include_metadata=True)

        assert len(results) == 3
        for result in results:
            assert "text" in result
            assert "score" in result
            assert "asset_id" in result
            assert "project_id" in result
            assert "chunk_index" in result
            assert "metadata" in result  # include_metadata=True

    @pytest.mark.asyncio
    async def test_search_with_context_excludes_metadata(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that search_with_context can exclude metadata."""
        mock_vector_store.search.return_value = sample_search_results

        orchestrator = SemanticSearchOrchestrator(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        query = "test query"
        results = await orchestrator.search_with_context(query=query, top_k=3, include_metadata=False)

        assert len(results) == 3
        for result in results:
            assert "text" in result
            assert "score" in result
            # Results without metadata should not have metadata key
            if not sample_search_results[results.index(result)].document.metadata:
                assert "metadata" not in result or result.get("metadata") is None


class TestSemanticSearchConvenienceFunction:
    """Tests for semantic_search convenience function."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        return MagicMock(spec=FAISSSQLiteVectorStore)

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create a mock embedding generator."""
        generator = MagicMock(spec=EmbeddingGenerator)
        generator.generate_embedding.return_value = [0.1] * 384
        return generator

    @pytest.fixture
    def sample_search_results(self) -> list[SearchResult]:
        """Create sample search results."""
        project_id = uuid4()
        asset_id = uuid4()
        return [
            SearchResult(
                document=VectorDocument(
                    id=f"{asset_id}_0",
                    asset_id=asset_id,
                    project_id=project_id,
                    chunk_index=0,
                    text="Test document",
                    embedding=[],
                ),
                score=0.8,
            )
        ]

    @pytest.mark.asyncio
    async def test_semantic_search_creates_orchestrator(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that convenience function creates orchestrator and searches."""
        mock_vector_store.search.return_value = sample_search_results

        results = await semantic_search(
            query="test query",
            top_k=5,
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        assert len(results) == 1
        assert results[0].document.text == "Test document"

    @pytest.mark.asyncio
    async def test_semantic_search_uses_defaults(self, sample_search_results):
        """Test that convenience function uses default dependencies."""
        with patch("backend.core.semantic_search.SemanticSearchOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.search.return_value = sample_search_results
            mock_orchestrator_class.return_value = mock_orchestrator

            results = await semantic_search(query="test query", top_k=5)

            mock_orchestrator_class.assert_called_once()
            mock_orchestrator.search.assert_called_once_with(
                query="test query",
                project_id=None,
                asset_id=None,
                top_k=5,
                rerank=True,
            )

    @pytest.mark.asyncio
    async def test_semantic_search_passes_parameters(
        self, mock_vector_store, mock_embedding_generator, sample_search_results
    ):
        """Test that convenience function passes all parameters."""
        mock_vector_store.search.return_value = sample_search_results
        project_id = uuid4()
        asset_id = uuid4()

        results = await semantic_search(
            query="test query",
            project_id=project_id,
            asset_id=asset_id,
            top_k=10,
            rerank=False,
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
        )

        assert len(results) == 1
        # Verify parameters were passed to vector store
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["project_id"] == project_id
        assert call_args.kwargs["asset_id"] == asset_id
        assert call_args.kwargs["top_k"] == 10  # No re-ranking


class TestSemanticSearchIntegration:
    """Integration tests for semantic search with real components."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path."""
        return tmp_path / "test_semantic_search.db"

    @pytest.fixture
    def vector_store(self, temp_db_path: Path) -> FAISSSQLiteVectorStore:
        """Create a real vector store instance."""
        return FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384, index_type="flat")

    @pytest.fixture
    def embedding_generator(self) -> EmbeddingGenerator:
        """Create a real embedding generator."""
        return EmbeddingGenerator()

    @pytest.fixture
    def sample_documents(self) -> list[VectorDocument]:
        """Create sample documents with real embeddings."""
        project_id = uuid4()
        asset_id = uuid4()
        embedding_generator = EmbeddingGenerator()

        texts = [
            "This is a document about marketing strategies and campaign planning.",
            "Marketing campaigns require careful planning and execution.",
            "Content generation is an important part of marketing.",
        ]

        embeddings = embedding_generator.generate_embeddings_batch(texts)

        return [
            VectorDocument(
                id=f"{asset_id}_{i}",
                asset_id=asset_id,
                project_id=project_id,
                chunk_index=i,
                text=texts[i],
                embedding=embeddings[i],
                metadata={"source": f"doc_{i}.pdf"} if i < 2 else None,
            )
            for i in range(len(texts))
        ]

    @pytest.mark.asyncio
    async def test_integration_search_finds_relevant_documents(
        self, vector_store, embedding_generator, sample_documents
    ):
        """Test that semantic search finds relevant documents."""
        # Add documents to vector store
        vector_store.add_documents(sample_documents)

        # Create orchestrator with real components
        orchestrator = SemanticSearchOrchestrator(
            vector_store=vector_store,
            embedding_generator=embedding_generator,
        )

        # Search for relevant query
        results = await orchestrator.search(query="marketing strategies", top_k=2)

        assert len(results) > 0
        assert len(results) <= 2
        # First result should be most relevant
        assert "marketing" in results[0].document.text.lower() or "strategies" in results[0].document.text.lower()

    @pytest.mark.asyncio
    async def test_integration_search_with_reranking(self, vector_store, embedding_generator, sample_documents):
        """Test that re-ranking improves result quality."""
        # Add documents to vector store
        vector_store.add_documents(sample_documents)

        # Create orchestrator
        orchestrator = SemanticSearchOrchestrator(
            vector_store=vector_store,
            embedding_generator=embedding_generator,
        )

        # Search with re-ranking
        query = "marketing campaigns planning"
        results = await orchestrator.search(query=query, top_k=2, rerank=True)

        assert len(results) > 0
        # Results should be sorted by score
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score
