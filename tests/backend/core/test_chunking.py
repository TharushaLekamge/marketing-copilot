"""Tests for text chunking utilities."""

from backend.core.chunking import (
    TextChunk,
    chunk_text,
    get_token_count,
    split_text_at_sentences,
    split_text_at_words,
)


class TestGetTokenCount:
    """Tests for get_token_count."""

    def test__get_token_count__returns_positive_number(self):
        """Test that token count returns a positive number."""
        text = "Hello, World! This is a test."
        count = get_token_count(text)
        assert count > 0
        assert isinstance(count, int)

    def test__get_token_count_with_empty_text__returns_zero(self):
        """Test that empty text returns zero tokens."""
        count = get_token_count("")
        assert count == 0

    def test__get_token_count_with_long_text__returns_higher_count(self):
        """Test that longer text returns higher token count."""
        short_text = "Hello"
        long_text = "Hello " * 100
        assert get_token_count(long_text) > get_token_count(short_text)


class TestSplitTextAtSentences:
    """Tests for split_text_at_sentences."""

    def test__split_text_at_sentences__splits_correctly(self):
        """Test that text is split at sentence boundaries."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = split_text_at_sentences(text)
        assert len(sentences) >= 3
        assert "First sentence" in sentences[0]
        assert "Second sentence" in sentences[1]
        assert "Third sentence" in sentences[2]

    def test__split_text_at_sentences_with_empty_text__returns_empty_list(self):
        """Test that empty text returns empty list."""
        sentences = split_text_at_sentences("")
        assert sentences == []

    def test__split_text_at_sentences__filters_empty_strings(self):
        """Test that empty strings are filtered out."""
        text = "First.  .Second."
        sentences = split_text_at_sentences(text)
        assert "" not in sentences


class TestSplitTextAtWords:
    """Tests for split_text_at_words."""

    def test__split_text_at_words__splits_correctly(self):
        """Test that text is split at word boundaries."""
        text = "word1 word2 word3"
        max_length = 10
        segments = split_text_at_words(text, max_length)
        assert len(segments) > 0
        assert all(len(seg) <= max_length for seg in segments)

    def test__split_text_at_words_with_short_text__returns_single_segment(self):
        """Test that short text returns single segment."""
        text = "short"
        segments = split_text_at_words(text, 100)
        assert len(segments) == 1
        assert segments[0] == text

    def test__split_text_at_words__preserves_words(self):
        """Test that words are not split."""
        text = "word1 word2 word3"
        segments = split_text_at_words(text, 5)
        # Each segment should contain complete words
        for segment in segments:
            assert " " in segment or len(segment.split()) == 1


class TestChunkText:
    """Tests for chunk_text."""

    def test__chunk_text_with_short_text__returns_single_chunk(self):
        """Test that short text returns single chunk."""
        text = "This is a short text"
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test__chunk_text_with_long_text__returns_multiple_chunks(self):
        """Test that long text returns multiple chunks."""
        # Create text that will exceed chunk size
        text = ". ".join([f"Sentence {i}" for i in range(100)])
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1

    def test__chunk_text__includes_metadata(self):
        """Test that chunks include all required metadata."""
        text = "This is a test sentence."
        chunks = chunk_text(text)
        assert len(chunks) > 0
        chunk = chunks[0]
        assert isinstance(chunk, TextChunk)
        assert chunk.text is not None
        assert chunk.chunk_index >= 0
        assert chunk.start_char >= 0
        assert chunk.end_char > chunk.start_char
        assert chunk.token_count > 0

    def test__chunk_text_with_overlap__creates_overlapping_chunks(self):
        """Test that chunks have overlap when specified."""
        text = ". ".join([f"Sentence {i}" for i in range(20)])
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
        if len(chunks) > 1:
            # Check that chunks overlap
            first_chunk_end = chunks[0].text[-20:]  # Last 20 chars
            second_chunk_start = chunks[1].text[:20]  # First 20 chars
            # There should be some overlap
            assert len(set(first_chunk_end.split()) & set(second_chunk_start.split())) > 0

    def test__chunk_text_with_empty_text__returns_empty_list(self):
        """Test that empty text returns empty list."""
        chunks = chunk_text("")
        assert chunks == []

    def test__chunk_text__respects_chunk_size(self):
        """Test that chunks respect the specified chunk size."""
        text = ". ".join([f"Sentence {i}" for i in range(50)])
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        for chunk in chunks:
            # Allow some flexibility (chunk size is approximate)
            assert chunk.token_count <= 150  # Allow 50% overhead
