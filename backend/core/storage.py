"""File storage abstraction for asset management."""

import os
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from backend.config import get_settings

settings = get_settings()


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class FileNotFoundError(StorageError):
    """Raised when a file is not found in storage."""

    pass


class Storage:
    """Abstract storage interface for file operations."""

    def save(self, project_id: UUID, asset_id: UUID, filename: str, content: bytes) -> str:
        """Save file content to storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename
            content: File content as bytes

        Returns:
            str: Path where the file was saved

        Raises:
            StorageError: If file cannot be saved
        """
        raise NotImplementedError

    def read(self, project_id: UUID, asset_id: UUID, filename: str) -> bytes:
        """Read file content from storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Returns:
            bytes: File content

        Raises:
            FileNotFoundError: If file is not found
            StorageError: If file cannot be read
        """
        raise NotImplementedError

    def delete(self, project_id: UUID, asset_id: UUID, filename: str) -> None:
        """Delete file from storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Raises:
            FileNotFoundError: If file is not found
            StorageError: If file cannot be deleted
        """
        raise NotImplementedError

    def exists(self, project_id: UUID, asset_id: UUID, filename: str) -> bool:
        """Check if file exists in storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Returns:
            bool: True if file exists, False otherwise
        """
        raise NotImplementedError


class LocalStorage(Storage):
    """Local file system storage implementation."""

    def __init__(self, base_path: str | Path | None = None):
        """Initialize local storage.

        Args:
            base_path: Base directory for file storage. Defaults to 'uploads' in project root.
        """
        if base_path is None:
            # Default to 'uploads' directory in project root
            project_root = Path(__file__).resolve().parent.parent.parent
            base_path = project_root / "uploads"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, project_id: UUID, asset_id: UUID, filename: str) -> Path:
        """Get the full file path for an asset.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Returns:
            Path: Full file path
        """
        # Sanitize filename to prevent directory traversal
        safe_filename = self._sanitize_filename(filename)
        return self.base_path / str(project_id) / str(asset_id) / safe_filename

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal and other security issues.

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename
        """
        # Remove path components
        filename = os.path.basename(filename)
        # Remove any remaining path separators
        filename = filename.replace("/", "_").replace("\\", "_")
        # Remove null bytes
        filename = filename.replace("\x00", "")
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[: 255 - len(ext)] + ext
        return filename

    def save(self, project_id: UUID, asset_id: UUID, filename: str, content: bytes) -> str:
        """Save file content to local storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename
            content: File content as bytes

        Returns:
            str: Path where the file was saved (relative to base_path)

        Raises:
            StorageError: If file cannot be saved
        """
        file_path = self._get_file_path(project_id, asset_id, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_bytes(content)
            # Return relative path from base_path
            return str(file_path.relative_to(self.base_path))
        except OSError as e:
            raise StorageError(f"Failed to save file: {e}") from e

    def read(self, project_id: UUID, asset_id: UUID, filename: str) -> bytes:
        """Read file content from local storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Returns:
            bytes: File content

        Raises:
            FileNotFoundError: If file is not found
            StorageError: If file cannot be read
        """
        file_path = self._get_file_path(project_id, asset_id, filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        try:
            return file_path.read_bytes()
        except OSError as e:
            raise StorageError(f"Failed to read file: {e}") from e

    def delete(self, project_id: UUID, asset_id: UUID, filename: str) -> None:
        """Delete file from local storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Raises:
            FileNotFoundError: If file is not found
            StorageError: If file cannot be deleted
        """
        file_path = self._get_file_path(project_id, asset_id, filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        try:
            file_path.unlink()
            # Clean up empty directories
            try:
                file_path.parent.rmdir()
                file_path.parent.parent.rmdir()
            except OSError:
                # Directory not empty or other error, ignore
                pass
        except OSError as e:
            raise StorageError(f"Failed to delete file: {e}") from e

    def exists(self, project_id: UUID, asset_id: UUID, filename: str) -> bool:
        """Check if file exists in local storage.

        Args:
            project_id: ID of the project
            asset_id: ID of the asset
            filename: Original filename

        Returns:
            bool: True if file exists, False otherwise
        """
        file_path = self._get_file_path(project_id, asset_id, filename)
        return file_path.exists()


# Global storage instance
_storage: Storage | None = None


def get_storage() -> Storage:
    """Get storage instance.

    Returns:
        Storage: Storage instance (singleton)

    Example:
        ```python
        from backend.core.storage import get_storage

        storage = get_storage()
        storage.save(project_id, asset_id, filename, content)
        ```
    """
    global _storage
    if _storage is None:
        # Allow configuration via environment variable for Docker/cloud deployments
        storage_path = os.getenv("STORAGE_PATH")
        if storage_path:
            _storage = LocalStorage(base_path=Path(storage_path))
        else:
            # Default behavior: use 'uploads' directory in project root
            _storage = LocalStorage()
    return _storage
