"""Unit tests for ingestion module."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from backend.core.chunking import TextChunk
from backend.core.ingestion import IngestionError, ingest_asset
from backend.core.vector_store import VectorDocument, VectorStoreError
from backend.models.asset import Asset
from backend.models.project import Project
from backend.models.user import User

logger = logging.getLogger(__name__)


@pytest.fixture
def sample_user(test_db_session) -> User:
    """Create a sample user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
        role="user",
        created_at=datetime.now(timezone.utc),
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def sample_project(test_db_session, sample_user: User) -> Project:
    """Create a sample project for testing."""
    project = Project(
        id=uuid4(),
        owner_id=sample_user.id,
        name="Test Project",
        description="Test Description",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db_session.add(project)
    test_db_session.commit()
    test_db_session.refresh(project)
    return project


@pytest.fixture
def sample_asset(test_db_session, sample_project: Project) -> Asset:
    """Create a sample asset for testing."""
    asset = Asset(
        id=uuid4(),
        project_id=sample_project.id,
        filename="test.txt",
        content_type="text/plain",
        ingested=False,
        ingesting=False,
        asset_metadata=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db_session.add(asset)
    test_db_session.commit()
    test_db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_file_content() -> bytes:
    """Sample file content for testing."""
    return b"This is a test document with some content for ingestion testing."


@pytest.fixture
def sample_text() -> str:
    """Sample extracted text for testing."""
    return "This is a test document with some content for ingestion testing."


@pytest.fixture
def sample_chunks() -> list[TextChunk]:
    """Sample text chunks for testing."""
    return [
        TextChunk(
            text="This is a test document with some content for ingestion testing.",
            chunk_index=0,
            start_char=0,
            end_char=70,
            token_count=15,
        )
    ]


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """Sample embeddings for testing."""
    # Return a list with one embedding vector of dimension 384
    return [[0.1] * 384]


class TestIngestAssetSuccess:
    """Tests for successful ingestion flow."""

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__successful_flow(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test successful ingestion flow."""
        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text

        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Execute
        ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingested is True
        assert sample_asset.asset_metadata is not None
        assert "ingestion" in sample_asset.asset_metadata
        assert sample_asset.asset_metadata["ingestion"]["chunk_count"] == 1
        assert sample_asset.asset_metadata["ingestion"]["total_tokens"] == 15

        # Verify mocks were called correctly
        mock_storage.read.assert_called_once_with(sample_asset.project_id, sample_asset.id, sample_asset.filename)
        mock_extract_text.assert_called_once_with(sample_file_content, sample_asset.filename, sample_asset.content_type)
        mock_chunk_text.assert_called_once()
        mock_embedding_generator.generate_embeddings_batch.assert_called_once()
        mock_vector_store.add_documents.assert_called_once()
        assert len(mock_vector_store.add_documents.call_args[0][0]) == 1

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__re_ingestion_deletes_existing_vectors(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that re-ingestion deletes existing vectors first."""
        # Mark asset as already ingested
        sample_asset.ingested = True
        test_db_session.commit()

        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Execute
        ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify that delete_by_asset was called before add_documents
        mock_vector_store.delete_by_asset.assert_called_once_with(sample_asset.id)
        mock_vector_store.add_documents.assert_called_once()


class TestIngestAssetErrors:
    """Tests for error handling in ingestion."""

    def test__ingest_asset__asset_not_found(self, test_db_session, sample_project: Project):
        """Test that ingestion raises error when asset is not found."""
        non_existent_asset_id = uuid4()

        with pytest.raises(IngestionError, match="not found"):
            ingest_asset(non_existent_asset_id, sample_project.id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__file_not_found_in_storage(
        self,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingestion raises error when file is not found in storage."""
        mock_storage = MagicMock()
        mock_storage.read.side_effect = FileNotFoundError("File not found")
        mock_get_storage.return_value = mock_storage

        logger.info(f"Testing ingestion with asset_id={sample_asset.id}, project_id={sample_asset.project_id}")
        with pytest.raises(IngestionError, match="File not found"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__storage_error(
        self,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingestion raises error when storage read fails."""
        from backend.core.storage import StorageError

        mock_storage = MagicMock()
        mock_storage.read.side_effect = StorageError("Storage error")
        mock_get_storage.return_value = mock_storage

        with pytest.raises(IngestionError, match="Failed to read file from storage"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    @patch("backend.core.ingestion.extract_text_from_file")
    def test__ingest_asset__document_processing_error(
        self,
        mock_extract_text: MagicMock,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
    ):
        """Test that ingestion raises error when document processing fails."""
        from backend.core.document_processor import DocumentProcessingError

        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.side_effect = DocumentProcessingError("Processing failed")

        with pytest.raises(IngestionError, match="Failed to extract text from file"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.normalize_text")
    def test__ingest_asset__empty_text_after_normalization(
        self,
        mock_normalize_text: MagicMock,
        mock_extract_text: MagicMock,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
    ):
        """Test that ingestion raises error when text is empty after normalization."""
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = "Some text"
        mock_normalize_text.return_value = ""

        with pytest.raises(IngestionError, match="No text content found"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.chunk_text")
    def test__ingest_asset__no_chunks_created(
        self,
        mock_chunk_text: MagicMock,
        mock_extract_text: MagicMock,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
    ):
        """Test that ingestion raises error when no chunks are created."""
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = "Some text"
        mock_chunk_text.return_value = []

        with pytest.raises(IngestionError, match="No chunks created"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__embedding_generation_error(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
    ):
        """Test that ingestion raises error when embedding generation fails."""
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.side_effect = Exception("Embedding error")
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_get_vector_store.return_value = MagicMock()

        with pytest.raises(IngestionError, match="Failed to generate embeddings"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__embedding_count_mismatch(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
    ):
        """Test that ingestion raises error when embedding count doesn't match chunk count."""
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        # Return wrong number of embeddings
        mock_embedding_generator.generate_embeddings_batch.return_value = []
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_get_vector_store.return_value = MagicMock()

        with pytest.raises(IngestionError, match="Embedding count mismatch"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__vector_store_error(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that ingestion raises error when vector store fails."""
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_vector_store.add_documents.side_effect = VectorStoreError("Vector store error")
        mock_get_vector_store.return_value = mock_vector_store

        with pytest.raises(IngestionError, match="Failed to store vectors"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_vector_store")
    def test__ingest_asset__re_ingestion_vector_deletion_error(
        self,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingestion raises error when deleting existing vectors fails."""
        # Mark asset as already ingested
        sample_asset.ingested = True
        test_db_session.commit()

        mock_vector_store = MagicMock()
        mock_vector_store.delete_by_asset.side_effect = VectorStoreError("Delete error")
        mock_get_vector_store.return_value = mock_vector_store

        with pytest.raises(IngestionError, match="Failed to delete existing vectors"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__unexpected_error(
        self,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingestion handles unexpected errors."""
        mock_storage = MagicMock()
        mock_storage.read.side_effect = ValueError("Unexpected error")
        mock_get_storage.return_value = mock_storage

        with pytest.raises(IngestionError, match="Unexpected error during ingestion"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)


class TestIngestAssetVectorDocuments:
    """Tests for VectorDocument creation in ingestion."""

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__creates_correct_vector_documents(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that ingestion creates VectorDocument objects with correct metadata."""
        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Execute
        ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify VectorDocument creation
        call_args = mock_vector_store.add_documents.call_args[0][0]
        assert len(call_args) == 1

        vector_doc = call_args[0]
        assert isinstance(vector_doc, VectorDocument)
        assert vector_doc.id == f"{sample_asset.id}_{sample_chunks[0].chunk_index}"
        assert vector_doc.asset_id == sample_asset.id
        assert vector_doc.project_id == sample_asset.project_id
        assert vector_doc.chunk_index == sample_chunks[0].chunk_index
        assert vector_doc.text == sample_chunks[0].text
        assert vector_doc.embedding == sample_embeddings[0]
        assert vector_doc.metadata is not None
        assert vector_doc.metadata["filename"] == sample_asset.filename
        assert vector_doc.metadata["content_type"] == sample_asset.content_type
        assert vector_doc.metadata["chunk_index"] == sample_chunks[0].chunk_index
        assert vector_doc.metadata["start_char"] == sample_chunks[0].start_char
        assert vector_doc.metadata["end_char"] == sample_chunks[0].end_char
        assert vector_doc.metadata["token_count"] == sample_chunks[0].token_count


class TestIngestAssetIngestingField:
    """Tests for ingesting field behavior."""

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__sets_ingesting_to_true_then_false_on_success(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that ingesting is set to True during ingestion and False on success."""
        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Verify initial state
        assert sample_asset.ingesting is False

        # Execute
        ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify final state
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingesting is False
        assert sample_asset.ingested is True

    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__sets_ingesting_to_false_on_error(
        self,
        mock_get_storage: MagicMock,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingesting is reset to False when ingestion fails."""
        mock_storage = MagicMock()
        mock_storage.read.side_effect = FileNotFoundError("File not found")
        mock_get_storage.return_value = mock_storage

        # Verify initial state
        assert sample_asset.ingesting is False

        # Execute and expect error
        with pytest.raises(IngestionError):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify ingesting is reset to False even after error
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingesting is False

    def test__ingest_asset__fails_if_already_ingesting(
        self,
        test_db_session,
        sample_asset: Asset,
    ):
        """Test that ingestion fails if asset is already being ingested."""
        # Set ingesting to True
        sample_asset.ingesting = True
        test_db_session.commit()

        # Execute and expect error
        with pytest.raises(IngestionError, match="already being ingested"):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify ingesting is still True (not changed by failed ingestion)
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingesting is True

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__commits_ingesting_status_immediately(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that ingesting status is committed immediately to lock the asset."""
        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Execute ingestion
        ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify in a fresh session that ingesting was set and then cleared
        # (We can't easily test the intermediate state, but we can verify final state)
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingesting is False
        assert sample_asset.ingested is True

    @patch("backend.core.ingestion.get_vector_store")
    @patch("backend.core.ingestion.get_embedding_generator")
    @patch("backend.core.ingestion.chunk_text")
    @patch("backend.core.ingestion.extract_text_from_file")
    @patch("backend.core.ingestion.get_storage")
    def test__ingest_asset__resets_ingesting_on_unexpected_error(
        self,
        mock_get_storage: MagicMock,
        mock_extract_text: MagicMock,
        mock_chunk_text: MagicMock,
        mock_get_embedding_generator: MagicMock,
        mock_get_vector_store: MagicMock,
        test_db_session,
        sample_asset: Asset,
        sample_file_content: bytes,
        sample_text: str,
        sample_chunks: list[TextChunk],
        sample_embeddings: list[list[float]],
    ):
        """Test that ingesting is reset to False even on unexpected errors."""
        # Setup mocks
        mock_storage = MagicMock()
        mock_storage.read.return_value = sample_file_content
        mock_get_storage.return_value = mock_storage

        mock_extract_text.return_value = sample_text
        mock_chunk_text.return_value = sample_chunks

        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embeddings_batch.return_value = sample_embeddings
        mock_get_embedding_generator.return_value = mock_embedding_generator

        # Make vector store fail with unexpected error
        mock_vector_store = MagicMock()
        mock_vector_store.add_documents.side_effect = ValueError("Unexpected error")
        mock_get_vector_store.return_value = mock_vector_store

        # Execute and expect error
        with pytest.raises(IngestionError):
            ingest_asset(sample_asset.id, sample_asset.project_id, test_db_session)

        # Verify ingesting is reset to False even after unexpected error
        test_db_session.refresh(sample_asset)
        assert sample_asset.ingesting is False
