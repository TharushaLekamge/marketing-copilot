"""Document processing utilities for text extraction."""

import io
import os

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    pass


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content.

    Args:
        content: PDF file content as bytes

    Returns:
        str: Extracted text from the PDF

    Raises:
        DocumentProcessingError: If PDF processing fails
    """
    try:
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts)
    except Exception as e:
        raise DocumentProcessingError(f"Failed to extract text from PDF: {str(e)}") from e


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content.

    Args:
        content: DOCX file content as bytes

    Returns:
        str: Extracted text from the DOCX

    Raises:
        DocumentProcessingError: If DOCX processing fails
    """
    try:
        docx_file = io.BytesIO(content)
        doc = Document(docx_file)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        return "\n".join(text_parts)
    except Exception as e:
        raise DocumentProcessingError(f"Failed to extract text from DOCX: {str(e)}") from e


def extract_text_from_txt(content: bytes, encoding: str = "utf-8") -> str:
    """Extract text from plain text content.

    Args:
        content: Text file content as bytes
        encoding: Text encoding (default: utf-8)

    Returns:
        str: Extracted text

    Raises:
        DocumentProcessingError: If text processing fails
    """
    try:
        # Try UTF-8 first
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to Latin-1 if UTF-8 fails
            return content.decode("latin-1")
    except Exception as e:
        raise DocumentProcessingError(f"Failed to extract text from TXT: {str(e)}") from e


def extract_text_from_html(content: bytes, encoding: str = "utf-8") -> str:
    """Extract text from HTML content.

    Args:
        content: HTML file content as bytes
        encoding: Text encoding (default: utf-8)

    Returns:
        str: Extracted text (HTML tags removed)

    Raises:
        DocumentProcessingError: If HTML processing fails
    """
    try:
        # Decode HTML content
        try:
            html_text = content.decode(encoding)
        except UnicodeDecodeError:
            html_text = content.decode("latin-1")

        # Parse HTML and extract text
        soup = BeautifulSoup(html_text, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and normalize whitespace
        text = soup.get_text(separator="\n", strip=True)
        return text
    except Exception as e:
        raise DocumentProcessingError(f"Failed to extract text from HTML: {str(e)}") from e


def extract_text_from_file(content: bytes, filename: str, content_type: str | None = None) -> str:
    """Extract text from a file based on its extension or content type.

    Args:
        content: File content as bytes
        filename: Original filename
        content_type: MIME type of the file (optional)

    Returns:
        str: Extracted text

    Raises:
        DocumentProcessingError: If file format is unsupported or processing fails
    """
    if not filename:
        raise DocumentProcessingError("Filename is required")

    # Get file extension
    _, ext = os.path.splitext(filename.lower())

    # Map extensions to extraction functions
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".doc": extract_text_from_docx,  # Try DOCX extractor for .doc files
        ".txt": extract_text_from_txt,
        ".md": extract_text_from_txt,
        ".html": extract_text_from_html,
        ".htm": extract_text_from_html,
    }

    # Check if extension is supported
    if ext not in extractors:
        raise DocumentProcessingError(f"Unsupported file format: {ext}. Supported formats: PDF, DOCX, TXT, MD, HTML")

    # Extract text
    try:
        text = extractors[ext](content)
        if not text or not text.strip():
            raise DocumentProcessingError("No text content found in file")
        return text
    except DocumentProcessingError:
        raise
    except Exception as e:
        raise DocumentProcessingError(f"Failed to process file {filename}: {str(e)}") from e


def normalize_text(text: str) -> str:
    """Normalize extracted text.

    Args:
        text: Raw extracted text

    Returns:
        str: Normalized text
    """
    # Remove excessive whitespace
    lines = text.split("\n")
    normalized_lines = []

    for line in lines:
        # Strip each line
        line = line.strip()
        # Skip empty lines
        if line:
            normalized_lines.append(line)

    # Join with single newline
    normalized = "\n".join(normalized_lines)

    # Replace multiple spaces with single space
    while "  " in normalized:
        normalized = normalized.replace("  ", " ")

    return normalized
