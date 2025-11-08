"""Ingestion pipeline orchestration for document processing and vector storage."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from backend.core.chunking import chunk_text
from backend.core.document_processing import (
    DocumentProcessingError,
    extract_text_from_file,
    normalize_text,
)
from backend.core.embeddings import get_embedding_generator
from backend.core.storage import FileNotFoundError, StorageError, get_storage
from backend.core.vector_store import VectorDocument, VectorStoreError, get_vector_store
from backend.models.asset import Asset

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when ingestion fails."""

    pass


def ingest_asset(asset_id: UUID, project_id: UUID, db: Session) -> None:
    """Ingest an asset: extract text, chunk, embed, and store in vector database.

    This function orchestrates the complete ingestion pipeline:
    1. Read file from storage
    2. Extract text from file
    3. Normalize text
    4. Chunk text into smaller pieces
    5. Generate embeddings for each chunk
    6. Store chunks in vector store
    7. Update asset ingestion status

    Args:
        asset_id: ID of the asset to ingest
        project_id: ID of the project the asset belongs to
        db: Database session for updating asset status

    Raises:
        IngestionError: If ingestion fails at any step
    """
    logger.info(f"Starting ingestion for asset {asset_id} in project {project_id}")

    # Get asset from database
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        logger.error(f"Asset {asset_id} not found in project {project_id}")
        raise IngestionError(f"Asset {asset_id} not found in project {project_id}")

    # Check if already ingesting
    if asset.ingesting:
        logger.warning(f"Asset {asset_id} is already being ingested")
        raise IngestionError(f"Asset {asset_id} is already being ingested")

    # Set ingesting status and commit immediately to lock the asset
    asset.ingesting = True
    db.commit()
    logger.info(f"Set ingesting status for asset {asset_id}")

    # Check if already ingested
    if asset.ingested:
        logger.warning(f"Asset {asset_id} already ingested, re-ingesting (deleting existing vectors)")
        # Optionally re-ingest: delete existing vectors first
        try:
            vector_store = get_vector_store()
            vector_store.delete_by_asset(asset_id)
        except VectorStoreError as e:
            logger.error(f"Failed to delete existing vectors for asset {asset_id}: {e}")
            raise IngestionError(f"Failed to delete existing vectors: {e}") from e

    try:
        # Step 1: Read file from storage
        storage = get_storage()
        try:
            file_content = storage.read(project_id, asset_id, asset.filename)
        except FileNotFoundError as e:
            raise IngestionError(f"File not found in storage: {e}") from e
        except StorageError as e:
            raise IngestionError(f"Failed to read file from storage: {e}") from e

        # Step 2: Extract text from file
        try:
            raw_text = extract_text_from_file(file_content, asset.filename, asset.content_type)
            logger.info(f"Extracted {len(raw_text)} characters from {asset.filename}")
        except DocumentProcessingError as e:
            logger.error(f"Failed to extract text from {asset.filename}: {e}")
            raise IngestionError(f"Failed to extract text from file: {e}") from e

        # Step 3: Normalize text
        normalized_text = normalize_text(raw_text)

        if not normalized_text.strip():
            logger.error(f"No text content found in {asset.filename} after normalization")
            raise IngestionError("No text content found in file after extraction and normalization")

        # Step 4: Chunk text
        text_chunks = chunk_text(normalized_text)

        if not text_chunks:
            logger.error(f"No chunks created from text in {asset.filename}")
            raise IngestionError("No chunks created from text")

        logger.info(f"Created {len(text_chunks)} chunks from {asset.filename}")

        # Step 5: Generate embeddings for chunks
        embedding_generator = get_embedding_generator()
        chunk_texts = [chunk.text for chunk in text_chunks]

        try:
            embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)
            logger.info(f"Generated embeddings for {len(embeddings)} chunks")
        except Exception as e:
            logger.error(f"Failed to generate embeddings for asset {asset_id}: {e}")
            raise IngestionError(f"Failed to generate embeddings: {e}") from e

        if len(embeddings) != len(text_chunks):
            logger.error(f"Embedding count mismatch: expected {len(text_chunks)}, got {len(embeddings)}")
            raise IngestionError(f"Embedding count mismatch: expected {len(text_chunks)}, got {len(embeddings)}")

        # Step 6: Create VectorDocument objects and store in vector store
        vector_documents = []
        for chunk, embedding in zip(text_chunks, embeddings):
            vector_id = f"{asset_id}_{chunk.chunk_index}"
            metadata = {
                "filename": asset.filename,
                "content_type": asset.content_type,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "token_count": chunk.token_count,
            }

            vector_doc = VectorDocument(
                id=vector_id,
                asset_id=asset_id,
                project_id=project_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                embedding=embedding,
                metadata=metadata,
            )
            vector_documents.append(vector_doc)

        # Store in vector store
        vector_store = get_vector_store()
        try:
            vector_store.add_documents(vector_documents)
            logger.info(f"Stored {len(vector_documents)} vector documents in vector store")
        except VectorStoreError as e:
            logger.error(f"Failed to store vectors for asset {asset_id}: {e}")
            raise IngestionError(f"Failed to store vectors: {e}") from e

        # Step 7: Update asset ingestion status
        asset.ingested = True
        asset.ingesting = False
        # Update metadata with ingestion info
        if asset.asset_metadata is None:
            asset.asset_metadata = {}
        total_tokens = sum(chunk.token_count for chunk in text_chunks)
        asset.asset_metadata["ingestion"] = {
            "chunk_count": len(text_chunks),
            "total_tokens": total_tokens,
        }

        db.commit()
        logger.info(f"Successfully ingested asset {asset_id}: {len(text_chunks)} chunks, {total_tokens} tokens")

    except IngestionError:
        # Re-raise ingestion errors (already logged)
        # Reset ingesting status on error
        try:
            asset.ingesting = False
            db.commit()
        except Exception:
            # If commit fails, rollback
            db.rollback()
        raise
    except Exception as e:
        # Wrap unexpected errors
        logger.exception(f"Unexpected error during ingestion of asset {asset_id}")
        # Reset ingesting status on error
        try:
            asset.ingesting = False
            db.commit()
        except Exception:
            # If commit fails, rollback
            db.rollback()
        raise IngestionError(f"Unexpected error during ingestion: {e}") from e
