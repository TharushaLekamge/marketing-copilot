"""Semantic search orchestration using Semantic Kernel."""

import logging
from typing import List, Optional
from uuid import UUID

from semantic_kernel import Kernel

from backend.core.embeddings import EmbeddingGenerator, get_embedding_generator
from backend.core.vector_store import SearchResult, VectorStore, VectorStoreError, get_vector_store

logger = logging.getLogger(__name__)


class SemanticSearchError(Exception):
    """Exception raised during semantic search."""

    pass


class SemanticSearchOrchestrator:
    """Orchestrates semantic search using Semantic Kernel and vector store."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        kernel: Optional[Kernel] = None,
    ):
        """Initialize the semantic search orchestrator.

        Args:
            vector_store: Vector store instance (defaults to global instance)
            embedding_generator: Embedding generator instance (defaults to global instance)
            kernel: Semantic Kernel instance (optional, for future use)
        """
        self.vector_store = vector_store or get_vector_store()
        self.embedding_generator = embedding_generator or get_embedding_generator()
        self.kernel = kernel or Kernel()

    async def search(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        asset_id: Optional[UUID] = None,
        top_k: int = 10,
        rerank: bool = False,
    ) -> List[SearchResult]:
        """Perform semantic search with optional re-ranking.

        Args:
            query: Search query text
            project_id: Optional project ID to filter results
            asset_id: Optional asset ID to filter results
            top_k: Number of results to return
            rerank: Whether to apply re-ranking to results

        Returns:
            List of search results sorted by relevance (highest first)

        Raises:
            SemanticSearchError: If search fails
        """
        try:
            if not query or not query.strip():
                logger.warning("Empty query provided to semantic search")
                return []

            # Step 1: Generate query embedding
            logger.debug(f"Generating embedding for query: {query[:50]}...")
            query_embedding = self.embedding_generator.generate_embedding(query.strip())

            # Step 2: Perform k-NN search in vector store
            # Get more results than requested for re-ranking
            search_k = top_k * 3 if rerank else top_k
            logger.debug(f"Searching vector store with top_k={search_k}")
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=search_k,
                project_id=project_id,
                asset_id=asset_id,
            )

            if not results:
                logger.info("No results found in vector store")
                return []

            # Step 3: Re-rank results if enabled
            if rerank and len(results) > 1:
                logger.debug(f"Re-ranking {len(results)} results")
                results = self._rerank_results(query, results)

            # Step 4: Return top_k results
            return results[:top_k]

        except VectorStoreError as e:
            logger.error(f"Vector store error during semantic search: {e}")
            raise SemanticSearchError(f"Vector store search failed: {e}") from e
        except Exception as e:
            logger.error(f"Error during semantic search: {e}", exc_info=True)
            raise SemanticSearchError(f"Semantic search failed: {e}") from e

    def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Re-rank search results using multiple factors.

        Args:
            query: Original search query
            results: Initial search results from vector store

        Returns:
            Re-ranked list of search results
        """
        if not results:
            return results

        # Calculate re-ranking scores for each result
        reranked = []
        for result in results:
            # Base similarity score from vector search
            similarity_score = result.score

            # Additional scoring factors
            text = result.document.text.lower()
            query_lower = query.lower()

            # Keyword match boost (exact matches get higher score)
            keyword_boost = 0.0
            query_words = query_lower.split()
            matched_words = sum(1 for word in query_words if word in text)
            if matched_words > 0:
                keyword_boost = min(0.2, matched_words / len(query_words) * 0.2)

            # Text length normalization (prefer medium-length chunks)
            text_length = len(result.document.text)
            length_score = 0.0
            if 100 <= text_length <= 500:
                length_score = 0.1  # Optimal length
            elif text_length < 50:
                length_score = -0.05  # Too short
            elif text_length > 1000:
                length_score = -0.05  # Too long

            # Metadata boost (if available)
            metadata_boost = 0.0
            if result.document.metadata:
                # Boost results with rich metadata
                metadata_keys = len(result.document.metadata)
                if metadata_keys > 0:
                    metadata_boost = min(0.1, metadata_keys * 0.02)

            # Combine scores
            final_score = similarity_score + keyword_boost + length_score + metadata_boost

            # Create new result with re-ranked score
            reranked.append(SearchResult(document=result.document, score=final_score))

        # Sort by final score (descending)
        reranked.sort(key=lambda x: x.score, reverse=True)

        return reranked

    async def search_with_context(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        asset_id: Optional[UUID] = None,
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> List[dict]:
        """Perform semantic search and return results with formatted context.

        Args:
            query: Search query text
            project_id: Optional project ID to filter results
            asset_id: Optional asset ID to filter results
            top_k: Number of results to return
            include_metadata: Whether to include metadata in results

        Returns:
            List of dictionaries with formatted search results including:
            - text: Document text
            - score: Similarity score
            - asset_id: Asset ID
            - project_id: Project ID
            - chunk_index: Chunk index
            - metadata: Optional metadata dict

        Raises:
            SemanticSearchError: If search fails
        """
        results = await self.search(
            query=query,
            project_id=project_id,
            asset_id=asset_id,
            top_k=top_k,
            rerank=True,
        )

        formatted_results = []
        for result in results:
            formatted = {
                "text": result.document.text,
                "score": result.score,
                "asset_id": str(result.document.asset_id),
                "project_id": str(result.document.project_id),
                "chunk_index": result.document.chunk_index,
            }
            if include_metadata and result.document.metadata:
                formatted["metadata"] = result.document.metadata

            formatted_results.append(formatted)

        return formatted_results


async def semantic_search(
    query: str,
    project_id: Optional[UUID] = None,
    asset_id: Optional[UUID] = None,
    top_k: int = 10,
    rerank: bool = True,
    vector_store: Optional[VectorStore] = None,
    embedding_generator: Optional[EmbeddingGenerator] = None,
) -> List[SearchResult]:
    """Perform semantic search (convenience function).

    This is a convenience function that creates an orchestrator and performs search.

    Args:
        query: Search query text
        project_id: Optional project ID to filter results
        asset_id: Optional asset ID to filter results
        top_k: Number of results to return
        rerank: Whether to apply re-ranking to results
        vector_store: Optional vector store instance
        embedding_generator: Optional embedding generator instance

    Returns:
        List of search results sorted by relevance (highest first)

    Raises:
        SemanticSearchError: If search fails
    """
    orchestrator = SemanticSearchOrchestrator(
        vector_store=vector_store,
        embedding_generator=embedding_generator,
    )
    return await orchestrator.search(
        query=query,
        project_id=project_id,
        asset_id=asset_id,
        top_k=top_k,
        rerank=rerank,
    )
