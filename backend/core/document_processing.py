"""High-level document processing utilities combining extraction and chunking."""

from typing import List

from backend.core.chunking import TextChunk, chunk_text
from backend.core.document_processor import (
    extract_text_from_file,
    normalize_text,
)


def process_document(
    content: bytes,
    filename: str,
    content_type: str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[TextChunk]:
    """Process a document: extract text, normalize, and chunk.

    Args:
        content: File content as bytes
        filename: Original filename
        content_type: MIME type of the file (optional)
        chunk_size: Target number of tokens per chunk (default: 500)
        chunk_overlap: Number of tokens to overlap between chunks (default: 50)

    Returns:
        List[TextChunk]: List of text chunks with metadata

    Raises:
        DocumentProcessingError: If document processing fails
    """
    # Extract text from file
    raw_text = extract_text_from_file(content, filename, content_type)

    # Normalize text
    normalized_text = normalize_text(raw_text)

    # Chunk text
    chunks = chunk_text(normalized_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    return chunks
