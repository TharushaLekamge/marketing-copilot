"""Tests for document processor."""

import io

import pytest

from backend.core.document_processor import (
    DocumentProcessingError,
    extract_text_from_docx,
    extract_text_from_file,
    extract_text_from_html,
    extract_text_from_pdf,
    extract_text_from_txt,
    normalize_text,
)


class TestExtractTextFromTxt:
    """Tests for extract_text_from_txt."""

    def test__extract_text_from_utf8__returns_text(self):
        """Test extracting text from UTF-8 encoded file."""
        content = "Hello, World!\nThis is a test file.".encode("utf-8")
        result = extract_text_from_txt(content)
        assert result == "Hello, World!\nThis is a test file."

    def test__extract_text_from_latin1__returns_text(self):
        """Test extracting text from Latin-1 encoded file."""
        content = "Hello, World!".encode("latin-1")
        result = extract_text_from_txt(content, encoding="latin-1")
        assert result == "Hello, World!"

    def test__extract_text_with_fallback__handles_unicode_error(self):
        """Test that extraction falls back to Latin-1 if UTF-8 fails."""
        # Create content that's not valid UTF-8 but valid Latin-1
        content = b"\xff\xfe"  # Invalid UTF-8
        result = extract_text_from_txt(content)
        # Should not raise an error
        assert isinstance(result, str)


class TestExtractTextFromHtml:
    """Tests for extract_text_from_html."""

    def test__extract_text_from_html__removes_tags(self):
        """Test extracting text from HTML removes tags."""
        content = b"<html><body><p>Hello, World!</p></body></html>"
        result = extract_text_from_html(content)
        assert "Hello, World!" in result
        assert "<html>" not in result
        assert "<p>" not in result

    def test__extract_text_from_html__removes_script_and_style(self):
        """Test that script and style elements are removed."""
        content = b"<html><body><script>alert('test');</script><p>Hello</p></body></html>"
        result = extract_text_from_html(content)
        assert "Hello" in result
        assert "alert" not in result
        assert "<script>" not in result


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf."""

    def test__extract_text_from_invalid_pdf__raises_error(self):
        """Test that invalid PDF raises DocumentProcessingError."""
        content = b"Not a PDF file"
        with pytest.raises(DocumentProcessingError):
            extract_text_from_pdf(content)


class TestExtractTextFromDocx:
    """Tests for extract_text_from_docx."""

    def test__extract_text_from_invalid_docx__raises_error(self):
        """Test that invalid DOCX raises DocumentProcessingError."""
        content = b"Not a DOCX file"
        with pytest.raises(DocumentProcessingError):
            extract_text_from_docx(content)


class TestExtractTextFromFile:
    """Tests for extract_text_from_file."""

    def test__extract_text_from_txt_file__returns_text(self):
        """Test extracting text from TXT file."""
        content = "Hello, World!".encode("utf-8")
        result = extract_text_from_file(content, "test.txt")
        assert result == "Hello, World!"

    def test__extract_text_from_md_file__returns_text(self):
        """Test extracting text from MD file."""
        content = "# Hello\n\nWorld!".encode("utf-8")
        result = extract_text_from_file(content, "test.md")
        assert "# Hello" in result

    def test__extract_text_from_unsupported_format__raises_error(self):
        """Test that unsupported format raises DocumentProcessingError."""
        content = b"Some content"
        with pytest.raises(DocumentProcessingError) as exc_info:
            extract_text_from_file(content, "test.xyz")
        assert "Unsupported file format" in str(exc_info.value)

    def test__extract_text_from_empty_file__raises_error(self):
        """Test that empty file raises DocumentProcessingError."""
        content = b""
        with pytest.raises(DocumentProcessingError) as exc_info:
            extract_text_from_file(content, "test.txt")
        assert "No text content found" in str(exc_info.value)

    def test__extract_text_without_filename__raises_error(self):
        """Test that missing filename raises DocumentProcessingError."""
        content = b"Some content"
        with pytest.raises(DocumentProcessingError) as exc_info:
            extract_text_from_file(content, "")
        assert "Filename is required" in str(exc_info.value)


class TestNormalizeText:
    """Tests for normalize_text."""

    def test__normalize_text__removes_excessive_whitespace(self):
        """Test that normalization removes excessive whitespace."""
        text = "Hello    World\n\n\nTest"
        result = normalize_text(text)
        assert "  " not in result  # No double spaces
        assert "\n\n" not in result  # No double newlines

    def test__normalize_text__removes_empty_lines(self):
        """Test that normalization removes empty lines."""
        text = "Line 1\n\n\nLine 2"
        result = normalize_text(text)
        lines = result.split("\n")
        assert "" not in lines

    def test__normalize_text__preserves_structure(self):
        """Test that normalization preserves basic structure."""
        text = "Paragraph 1\n\nParagraph 2"
        result = normalize_text(text)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
