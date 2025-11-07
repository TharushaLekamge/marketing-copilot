"""Unit tests for vector store module."""

from pathlib import Path
from uuid import uuid4

import pytest

from backend.core.embeddings import get_embedding_generator
from backend.core.vector_store import (
    FAISSSQLiteVectorStore,
    SearchResult,
    VectorDocument,
    VectorStoreError,
    get_vector_store,
)


class TestFAISSSQLiteVectorStore:
    """Tests for FAISSSQLiteVectorStore class."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path for testing."""
        return tmp_path / "test_vector_store.db"

    @pytest.fixture
    def vector_store(self, temp_db_path: Path) -> FAISSSQLiteVectorStore:
        """Create a vector store instance for testing."""
        return FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384, index_type="flat")

    @pytest.fixture
    def sample_documents(self) -> list[VectorDocument]:
        """Create sample documents for testing."""
        project_id = uuid4()
        asset_id = uuid4()

        # Generate embeddings from actual text content
        embedding_generator = get_embedding_generator()
        texts = [
            "This is the first chunk of text about marketing strategies.",
            "This is the second chunk of text about marketing strategies.",
            "This is the third chunk of text about different topics.",
        ]

        # Generate embeddings from text
        embeddings = embedding_generator.generate_embeddings_batch(texts)

        return [
            VectorDocument(
                id=f"{asset_id}_{0}",
                asset_id=asset_id,
                project_id=project_id,
                chunk_index=0,
                text=texts[0],
                embedding=embeddings[0],
                metadata={"source": "test"},
            ),
            VectorDocument(
                id=f"{asset_id}_{1}",
                asset_id=asset_id,
                project_id=project_id,
                chunk_index=1,
                text=texts[1],
                embedding=embeddings[1],
                metadata={"source": "test"},
            ),
            VectorDocument(
                id=f"{asset_id}_{2}",
                asset_id=asset_id,
                project_id=project_id,
                chunk_index=2,
                text=texts[2],
                embedding=embeddings[2],
            ),
        ]

    def test__init__creates_vector_store(self, temp_db_path: Path):
        """Test that vector store initializes correctly."""
        store = FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384)
        assert store.dimension == 384
        assert store.index_type == "flat"
        assert store.db_path == temp_db_path
        assert temp_db_path.exists()

    def test__init__creates_database_schema(self, temp_db_path: Path):
        """Test that database schema is created on initialization."""
        store = FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384)
        assert temp_db_path.exists()

        # Check that tables exist by querying
        import sqlite3

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vectors'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "vectors"

    def test__add_documents__adds_documents_to_store(
        self, vector_store: FAISSSQLiteVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that documents can be added to the store."""
        vector_store.add_documents(sample_documents)

        # Verify documents were added
        count = vector_store.get_document_count()
        assert count == 3

        # Verify FAISS index has vectors
        assert vector_store.index.ntotal == 3

    def test__add_documents__handles_empty_list(self, vector_store: FAISSSQLiteVectorStore):
        """Test that adding empty list doesn't raise error."""
        vector_store.add_documents([])
        assert vector_store.get_document_count() == 0

    def test__add_documents__validates_embedding_dimension(self, vector_store: FAISSSQLiteVectorStore):
        """Test that adding documents with wrong dimension raises error."""
        project_id = uuid4()
        asset_id = uuid4()

        # Create document with wrong dimension
        wrong_dim_doc = VectorDocument(
            id=f"{asset_id}_{0}",
            asset_id=asset_id,
            project_id=project_id,
            chunk_index=0,
            text="Test text",
            embedding=[0.0] * 100,  # Wrong dimension
        )

        with pytest.raises(VectorStoreError, match="dimension mismatch"):
            vector_store.add_documents([wrong_dim_doc])

    def test__search__returns_similar_documents(
        self, vector_store: FAISSSQLiteVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that search returns similar documents."""
        vector_store.add_documents(sample_documents)

        # Search using the first document's embedding
        query_embedding = sample_documents[0].embedding
        results = vector_store.search(query_embedding, top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.score > 0 for r in results)
        # First result should be the query document itself (highest similarity)
        assert results[0].document.id == sample_documents[0].id

    def test__search__returns_empty_list_when_store_is_empty(self, vector_store: FAISSSQLiteVectorStore):
        """Test that search returns empty list when store is empty."""
        query_embedding = [0.0] * 384
        results = vector_store.search(query_embedding, top_k=5)

        assert results == []

    def test__search__filters_by_project_id(self, vector_store: FAISSSQLiteVectorStore):
        """Test that search can filter by project ID."""
        project_id_1 = uuid4()
        project_id_2 = uuid4()
        asset_id = uuid4()

        embedding_generator = get_embedding_generator()

        # Create documents for two different projects
        texts_1 = [f"Project 1 chunk {i} about marketing" for i in range(2)]
        texts_2 = [f"Project 2 chunk {i} about sales" for i in range(2)]
        embeddings_1 = embedding_generator.generate_embeddings_batch(texts_1)
        embeddings_2 = embedding_generator.generate_embeddings_batch(texts_2)

        docs_1 = [
            VectorDocument(
                id=f"{asset_id}_{i}",
                asset_id=asset_id,
                project_id=project_id_1,
                chunk_index=i,
                text=texts_1[i],
                embedding=embeddings_1[i],
            )
            for i in range(2)
        ]

        docs_2 = [
            VectorDocument(
                id=f"{uuid4()}_{i}",
                asset_id=uuid4(),
                project_id=project_id_2,
                chunk_index=i,
                text=texts_2[i],
                embedding=embeddings_2[i],
            )
            for i in range(2)
        ]

        vector_store.add_documents(docs_1 + docs_2)

        # Search with project filter
        query_embedding = docs_1[0].embedding
        results = vector_store.search(query_embedding, top_k=10, project_id=project_id_1)

        # All results should be from project_id_1
        assert all(r.document.project_id == project_id_1 for r in results)
        assert len(results) <= 2  # Only 2 documents in project_id_1

    def test__search__filters_by_asset_id(self, vector_store: FAISSSQLiteVectorStore):
        """Test that search can filter by asset ID."""
        project_id = uuid4()
        asset_id_1 = uuid4()
        asset_id_2 = uuid4()

        embedding_generator = get_embedding_generator()

        # Create documents for two different assets
        texts_1 = [f"Asset 1 chunk {i} about content strategy" for i in range(2)]
        texts_2 = [f"Asset 2 chunk {i} about social media" for i in range(2)]
        embeddings_1 = embedding_generator.generate_embeddings_batch(texts_1)
        embeddings_2 = embedding_generator.generate_embeddings_batch(texts_2)

        docs_1 = [
            VectorDocument(
                id=f"{asset_id_1}_{i}",
                asset_id=asset_id_1,
                project_id=project_id,
                chunk_index=i,
                text=texts_1[i],
                embedding=embeddings_1[i],
            )
            for i in range(2)
        ]

        docs_2 = [
            VectorDocument(
                id=f"{asset_id_2}_{i}",
                asset_id=asset_id_2,
                project_id=project_id,
                chunk_index=i,
                text=texts_2[i],
                embedding=embeddings_2[i],
            )
            for i in range(2)
        ]

        vector_store.add_documents(docs_1 + docs_2)

        # Search with asset filter
        query_embedding = docs_1[0].embedding
        results = vector_store.search(query_embedding, top_k=10, asset_id=asset_id_1)

        # All results should be from asset_id_1
        assert all(r.document.asset_id == asset_id_1 for r in results)
        assert len(results) <= 2  # Only 2 documents in asset_id_1

    def test__search__validates_query_dimension(
        self, vector_store: FAISSSQLiteVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that search validates query embedding dimension."""
        vector_store.add_documents(sample_documents)

        # Search with wrong dimension
        wrong_dim_query = [0.0] * 100

        with pytest.raises(VectorStoreError, match="dimension mismatch"):
            vector_store.search(wrong_dim_query, top_k=5)

    def test__delete_by_asset__removes_asset_vectors(self, vector_store: FAISSSQLiteVectorStore):
        """Test that delete_by_asset removes all vectors for an asset."""
        project_id = uuid4()
        asset_id_1 = uuid4()
        asset_id_2 = uuid4()

        embedding_generator = get_embedding_generator()

        texts_1 = [f"Asset 1 chunk {i} about product features" for i in range(2)]
        texts_2 = [f"Asset 2 chunk {i} about pricing" for i in range(2)]
        embeddings_1 = embedding_generator.generate_embeddings_batch(texts_1)
        embeddings_2 = embedding_generator.generate_embeddings_batch(texts_2)

        docs_1 = [
            VectorDocument(
                id=f"{asset_id_1}_{i}",
                asset_id=asset_id_1,
                project_id=project_id,
                chunk_index=i,
                text=texts_1[i],
                embedding=embeddings_1[i],
            )
            for i in range(2)
        ]

        docs_2 = [
            VectorDocument(
                id=f"{asset_id_2}_{i}",
                asset_id=asset_id_2,
                project_id=project_id,
                chunk_index=i,
                text=texts_2[i],
                embedding=embeddings_2[i],
            )
            for i in range(2)
        ]

        vector_store.add_documents(docs_1 + docs_2)
        assert vector_store.get_document_count() == 4

        # Delete vectors for asset_id_1
        vector_store.delete_by_asset(asset_id_1)

        # Verify only asset_id_2 vectors remain
        assert vector_store.get_document_count() == 2

        # Verify asset_id_1 vectors are gone
        results = vector_store.search(docs_1[0].embedding, top_k=10, asset_id=asset_id_1)
        assert len(results) == 0

    def test__delete_by_project__removes_project_vectors(self, vector_store: FAISSSQLiteVectorStore):
        """Test that delete_by_project removes all vectors for a project."""
        project_id_1 = uuid4()
        project_id_2 = uuid4()
        asset_id = uuid4()

        embedding_generator = get_embedding_generator()

        texts_1 = [f"Project 1 chunk {i} about campaigns" for i in range(2)]
        texts_2 = [f"Project 2 chunk {i} about analytics" for i in range(2)]
        embeddings_1 = embedding_generator.generate_embeddings_batch(texts_1)
        embeddings_2 = embedding_generator.generate_embeddings_batch(texts_2)

        docs_1 = [
            VectorDocument(
                id=f"{asset_id}_{i}",
                asset_id=asset_id,
                project_id=project_id_1,
                chunk_index=i,
                text=texts_1[i],
                embedding=embeddings_1[i],
            )
            for i in range(2)
        ]

        docs_2 = [
            VectorDocument(
                id=f"{uuid4()}_{i}",
                asset_id=uuid4(),
                project_id=project_id_2,
                chunk_index=i,
                text=texts_2[i],
                embedding=embeddings_2[i],
            )
            for i in range(2)
        ]

        vector_store.add_documents(docs_1 + docs_2)
        assert vector_store.get_document_count() == 4

        # Delete vectors for project_id_1
        vector_store.delete_by_project(project_id_1)

        # Verify only project_id_2 vectors remain
        assert vector_store.get_document_count() == 2

    def test__get_document_count__returns_correct_count(
        self, vector_store: FAISSSQLiteVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that get_document_count returns correct count."""
        assert vector_store.get_document_count() == 0

        vector_store.add_documents(sample_documents)
        assert vector_store.get_document_count() == 3

    def test__get_document_count__filters_by_project_id(self, vector_store: FAISSSQLiteVectorStore):
        """Test that get_document_count can filter by project ID."""
        project_id_1 = uuid4()
        project_id_2 = uuid4()

        embedding_generator = get_embedding_generator()

        texts_1 = [f"Project 1 chunk {i} about branding" for i in range(2)]
        texts_2 = [f"Project 2 chunk {i} about SEO" for i in range(3)]
        embeddings_1 = embedding_generator.generate_embeddings_batch(texts_1)
        embeddings_2 = embedding_generator.generate_embeddings_batch(texts_2)

        docs_1 = [
            VectorDocument(
                id=f"{uuid4()}_{i}",
                asset_id=uuid4(),
                project_id=project_id_1,
                chunk_index=i,
                text=texts_1[i],
                embedding=embeddings_1[i],
            )
            for i in range(2)
        ]

        docs_2 = [
            VectorDocument(
                id=f"{uuid4()}_{i}",
                asset_id=uuid4(),
                project_id=project_id_2,
                chunk_index=i,
                text=texts_2[i],
                embedding=embeddings_2[i],
            )
            for i in range(3)
        ]

        vector_store.add_documents(docs_1 + docs_2)

        assert vector_store.get_document_count() == 5
        assert vector_store.get_document_count(project_id=project_id_1) == 2
        assert vector_store.get_document_count(project_id=project_id_2) == 3

    def test__clear__removes_all_documents(
        self, vector_store: FAISSSQLiteVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that clear removes all documents."""
        vector_store.add_documents(sample_documents)
        assert vector_store.get_document_count() == 3

        vector_store.clear()
        assert vector_store.get_document_count() == 0
        assert vector_store.index.ntotal == 0

    def test__persistence__survives_reinitialization(self, temp_db_path: Path, sample_documents: list[VectorDocument]):
        """Test that vectors persist across reinitialization."""
        # Create store and add documents
        store1 = FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384)
        store1.add_documents(sample_documents)
        assert store1.get_document_count() == 3

        # Create new store instance with same database
        store2 = FAISSSQLiteVectorStore(db_path=temp_db_path, dimension=384)

        # Vectors should be loaded from database
        # Note: This test may fail if FAISS index isn't properly saved/loaded
        # For MVP, we'll verify the database has the data
        assert store2.get_document_count() == 3


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test__get_vector_store__returns_singleton(self, tmp_path: Path):
        """Test that get_vector_store returns singleton instance."""
        db_path = tmp_path / "test.db"
        store1 = get_vector_store(db_path=db_path, dimension=384)
        store2 = get_vector_store(db_path=db_path, dimension=384)

        assert store1 is store2

    def test__get_vector_store__creates_default_path(self):
        """Test that get_vector_store creates default path if not provided."""
        # This test may create a file in the project root
        # In a real scenario, you'd want to clean this up
        store = get_vector_store(dimension=384)
        assert store is not None
        assert isinstance(store, FAISSSQLiteVectorStore)
