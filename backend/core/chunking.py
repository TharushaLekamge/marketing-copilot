"""Text chunking utilities for document processing."""

import re
from dataclasses import dataclass
from typing import List

import tiktoken


# Default chunking parameters
DEFAULT_CHUNK_SIZE = 500  # tokens per chunk
DEFAULT_CHUNK_OVERLAP = 50  # tokens overlap between chunks

# Encoding model for token counting (using cl100k_base which is used by GPT-4)
ENCODING_NAME = "cl100k_base"


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int


def get_token_count(text: str, encoding_name: str = ENCODING_NAME) -> int:
    """Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        encoding_name: Encoding model name (default: cl100k_base)

    Returns:
        int: Number of tokens
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback to approximate token count (roughly 4 characters per token)
        return len(text) // 4


def split_text_at_sentences(text: str) -> List[str]:
    """Split text into sentences.

    Args:
        text: Text to split

    Returns:
        List[str]: List of sentences
    """
    # Pattern to match sentence endings (period, exclamation, question mark)
    # Followed by whitespace or end of string
    sentence_pattern = r"[.!?]+(?:\s+|$)"
    sentences = re.split(sentence_pattern, text)
    # Filter out empty strings
    return [s.strip() for s in sentences if s.strip()]


def split_text_at_words(text: str, max_length: int) -> List[str]:
    """Split text at word boundaries to fit within max_length.

    Args:
        text: Text to split
        max_length: Maximum length in characters

    Returns:
        List[str]: List of text segments
    """
    if len(text) <= max_length:
        return [text]

    words = text.split()
    segments = []
    current_segment = ""

    for word in words:
        # Check if adding this word would exceed max_length
        test_segment = f"{current_segment} {word}".strip()
        if len(test_segment) <= max_length:
            current_segment = test_segment
        else:
            # Save current segment and start new one
            if current_segment:
                segments.append(current_segment)
            current_segment = word

    # Add remaining segment
    if current_segment:
        segments.append(current_segment)

    return segments


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    encoding_name: str = ENCODING_NAME,
) -> List[TextChunk]:
    """Split text into chunks with specified size and overlap.

    Args:
        text: Text to chunk
        chunk_size: Target number of tokens per chunk
        chunk_overlap: Number of tokens to overlap between chunks
        encoding_name: Encoding model name for token counting

    Returns:
        List[TextChunk]: List of text chunks with metadata
    """
    if not text or not text.strip():
        return []

    chunks: List[TextChunk] = []
    current_chunk_text = ""
    current_chunk_start = 0
    chunk_index = 0

    # Split text into sentences for better chunking
    sentences = split_text_at_sentences(text)

    for sentence in sentences:
        # Test if adding this sentence would exceed chunk size
        test_chunk = f"{current_chunk_text} {sentence}".strip()
        test_token_count = get_token_count(test_chunk, encoding_name)

        if test_token_count <= chunk_size:
            current_chunk_text = test_chunk
        else:
            # Current chunk is full, save it
            if current_chunk_text:
                current_token_count = get_token_count(current_chunk_text, encoding_name)
                current_chunk_end = current_chunk_start + len(current_chunk_text)

                chunks.append(
                    TextChunk(
                        text=current_chunk_text,
                        chunk_index=chunk_index,
                        start_char=current_chunk_start,
                        end_char=current_chunk_end,
                        token_count=current_token_count,
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap from previous chunk
                if chunk_overlap > 0:
                    overlap_text = _extract_overlap_text(current_chunk_text, chunk_overlap, encoding_name)
                    current_chunk_text = f"{overlap_text} {sentence}".strip()
                    # Update start position accounting for overlap
                    current_chunk_start = current_chunk_end - len(overlap_text)
                else:
                    current_chunk_text = sentence
                    current_chunk_start = current_chunk_end

            # Check if single sentence exceeds chunk size
            sentence_token_count = get_token_count(sentence, encoding_name)
            if sentence_token_count > chunk_size:
                # Split sentence at word boundaries
                # Approximate character limit (roughly 4 chars per token)
                max_chars = chunk_size * 4
                sentence_parts = split_text_at_words(sentence, max_chars)

                for part in sentence_parts:
                    test_with_part = f"{current_chunk_text} {part}".strip() if current_chunk_text else part
                    test_with_part_tokens = get_token_count(test_with_part, encoding_name)

                    if test_with_part_tokens <= chunk_size:
                        # Add part to current chunk
                        if current_chunk_text:
                            current_chunk_text = f"{current_chunk_text} {part}"
                        else:
                            current_chunk_text = part
                    else:
                        # Part would exceed chunk size, save current chunk first
                        if current_chunk_text:
                            current_token_count = get_token_count(current_chunk_text, encoding_name)
                            current_chunk_end = current_chunk_start + len(current_chunk_text)

                            chunks.append(
                                TextChunk(
                                    text=current_chunk_text,
                                    chunk_index=chunk_index,
                                    start_char=current_chunk_start,
                                    end_char=current_chunk_end,
                                    token_count=current_token_count,
                                )
                            )
                            chunk_index += 1

                            # Start new chunk with overlap
                            if chunk_overlap > 0:
                                overlap_text = _extract_overlap_text(current_chunk_text, chunk_overlap, encoding_name)
                                current_chunk_text = f"{overlap_text} {part}".strip()
                                current_chunk_start = current_chunk_end - len(overlap_text)
                            else:
                                current_chunk_text = part
                                current_chunk_start = current_chunk_end

    # Add final chunk
    if current_chunk_text:
        current_token_count = get_token_count(current_chunk_text, encoding_name)
        current_chunk_end = current_chunk_start + len(current_chunk_text)

        chunks.append(
            TextChunk(
                text=current_chunk_text,
                chunk_index=chunk_index,
                start_char=current_chunk_start,
                end_char=current_chunk_end,
                token_count=current_token_count,
            )
        )

    return chunks


def _extract_overlap_text(text: str, overlap_tokens: int, encoding_name: str) -> str:
    """Extract the last N tokens from text for overlap.

    Args:
        text: Text to extract overlap from
        overlap_tokens: Number of tokens to extract
        encoding_name: Encoding model name

    Returns:
        str: Overlap text
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)
        overlap_tokens_list = tokens[-overlap_tokens:] if len(tokens) > overlap_tokens else tokens
        return encoding.decode(overlap_tokens_list)
    except Exception:
        # Fallback: use approximate character count (roughly 4 chars per token)
        overlap_chars = overlap_tokens * 4
        return text[-overlap_chars:] if len(text) > overlap_chars else text
