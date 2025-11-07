"""File validation and processing utilities."""

# Maximum file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Allowed file extensions (case-insensitive)
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".rtf",
    ".odt",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".bmp",
    # Spreadsheets
    ".xls",
    ".xlsx",
    ".csv",
    ".ods",
    # Presentations
    ".ppt",
    ".pptx",
    ".odp",
    # Archives
    ".zip",
    ".rar",
    ".7z",
    # Other
    ".json",
    ".xml",
    ".html",
    ".htm",
}


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


def validate_filename(filename: str) -> None:
    """Validate filename format and extension.

    Args:
        filename: Filename to validate

    Raises:
        FileValidationError: If filename is invalid
    """
    if not filename or not filename.strip():
        raise FileValidationError("Filename is required")

    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise FileValidationError("Filename contains invalid characters")

    # Check extension
    filename_lower = filename.lower()
    has_allowed_extension = any(filename_lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    if not has_allowed_extension:
        raise FileValidationError(f"File type not allowed. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}")


def validate_file_size(content: bytes) -> None:
    """Validate file size.

    Args:
        content: File content as bytes

    Raises:
        FileValidationError: If file size exceeds maximum
    """
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise FileValidationError(f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb}MB)")


def validate_file(file_content: bytes, filename: str) -> None:
    """Validate file content and filename.

    Args:
        file_content: File content as bytes
        filename: Filename to validate

    Raises:
        FileValidationError: If validation fails
    """
    validate_filename(filename)
    validate_file_size(file_content)
