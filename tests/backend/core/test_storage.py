"""Unit tests for LocalStorage class."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from backend.core.storage import FileNotFoundError, LocalStorage


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for storage tests."""
    storage_dir = tmp_path / "storage_test"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def storage(temp_storage_dir: Path) -> LocalStorage:
    """Create a LocalStorage instance for testing."""
    return LocalStorage(base_path=temp_storage_dir)


@pytest.fixture
def sample_project_id() -> UUID:
    """Sample project ID for testing."""
    return uuid4()


@pytest.fixture
def sample_asset_id() -> UUID:
    """Sample asset ID for testing."""
    return uuid4()


@pytest.fixture
def sample_filename() -> str:
    """Sample filename for testing."""
    return "test-document.pdf"


@pytest.fixture
def sample_content() -> bytes:
    """Sample file content for testing."""
    return b"Test file content for storage testing"


class TestLocalStorageSave:
    """Tests for LocalStorage.save() method."""

    def test__save_file__creates_file_in_correct_location(
        self,
        storage: LocalStorage,
        sample_project_id: UUID,
        sample_asset_id: UUID,
        sample_filename: str,
        sample_content: bytes,
    ):
        """Test that save creates file in correct directory structure."""
        path = storage.save(sample_project_id, sample_asset_id, sample_filename, sample_content)

        # Verify path is returned
        assert isinstance(path, str)
        assert str(sample_project_id) in path
        assert str(sample_asset_id) in path
        assert sample_filename in path

        # Verify file exists
        file_path = storage._get_file_path(sample_project_id, sample_asset_id, sample_filename)
        assert file_path.exists()
        assert file_path.read_bytes() == sample_content

    def test__save_file__creates_directories_if_not_exist(
        self,
        storage: LocalStorage,
        sample_project_id: UUID,
        sample_asset_id: UUID,
        sample_filename: str,
        sample_content: bytes,
    ):
        """Test that save creates parent directories if they don't exist."""
        storage.save(sample_project_id, sample_asset_id, sample_filename, sample_content)

        file_path = storage._get_file_path(sample_project_id, sample_asset_id, sample_filename)
        assert file_path.parent.exists()
        assert file_path.parent.parent.exists()

    def test__save_file_with_sanitized_filename__handles_special_characters(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_content: bytes
    ):
        """Test that save sanitizes filenames with special characters."""
        unsafe_filename = "../../../etc/passwd"
        storage.save(sample_project_id, sample_asset_id, unsafe_filename, sample_content)

        file_path = storage._get_file_path(sample_project_id, sample_asset_id, unsafe_filename)
        # Verify path traversal was prevented
        assert "../../" not in str(file_path)
        assert "etc" not in str(file_path)
        assert file_path.exists()

    def test__save_file__overwrites_existing_file(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_filename: str
    ):
        """Test that save overwrites existing file."""
        original_content = b"Original content"
        new_content = b"New content"

        storage.save(sample_project_id, sample_asset_id, sample_filename, original_content)
        storage.save(sample_project_id, sample_asset_id, sample_filename, new_content)

        file_path = storage._get_file_path(sample_project_id, sample_asset_id, sample_filename)
        assert file_path.read_bytes() == new_content


class TestLocalStorageRead:
    """Tests for LocalStorage.read() method."""

    def test__read_existing_file__returns_file_content(
        self,
        storage: LocalStorage,
        sample_project_id: UUID,
        sample_asset_id: UUID,
        sample_filename: str,
        sample_content: bytes,
    ):
        """Test that read returns correct file content."""
        storage.save(sample_project_id, sample_asset_id, sample_filename, sample_content)

        content = storage.read(sample_project_id, sample_asset_id, sample_filename)

        assert content == sample_content

    def test__read_nonexistent_file__raises_file_not_found_error(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_filename: str
    ):
        """Test that read raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            storage.read(sample_project_id, sample_asset_id, sample_filename)

        assert "not found" in str(exc_info.value).lower()


class TestLocalStorageDelete:
    """Tests for LocalStorage.delete() method."""

    def test__delete_existing_file__removes_file(
        self,
        storage: LocalStorage,
        sample_project_id: UUID,
        sample_asset_id: UUID,
        sample_filename: str,
        sample_content: bytes,
    ):
        """Test that delete removes the file."""
        storage.save(sample_project_id, sample_asset_id, sample_filename, sample_content)
        file_path = storage._get_file_path(sample_project_id, sample_asset_id, sample_filename)
        assert file_path.exists()

        storage.delete(sample_project_id, sample_asset_id, sample_filename)

        assert not file_path.exists()

    def test__delete_nonexistent_file__raises_file_not_found_error(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_filename: str
    ):
        """Test that delete raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            storage.delete(sample_project_id, sample_asset_id, sample_filename)

        assert "not found" in str(exc_info.value).lower()


class TestLocalStorageExists:
    """Tests for LocalStorage.exists() method."""

    def test__exists_for_existing_file__returns_true(
        self,
        storage: LocalStorage,
        sample_project_id: UUID,
        sample_asset_id: UUID,
        sample_filename: str,
        sample_content: bytes,
    ):
        """Test that exists returns True for existing file."""
        storage.save(sample_project_id, sample_asset_id, sample_filename, sample_content)

        assert storage.exists(sample_project_id, sample_asset_id, sample_filename) is True

    def test__exists_for_nonexistent_file__returns_false(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_filename: str
    ):
        """Test that exists returns False for nonexistent file."""
        assert storage.exists(sample_project_id, sample_asset_id, sample_filename) is False


class TestLocalStorageSanitizeFilename:
    """Tests for LocalStorage._sanitize_filename() method."""

    def test__sanitize_filename__removes_path_components(self, storage: LocalStorage):
        """Test that sanitize removes path components."""
        unsafe = "../../../etc/passwd"
        safe = storage._sanitize_filename(unsafe)

        assert "/" not in safe
        assert ".." not in safe
        assert "passwd" in safe

    def test__sanitize_filename__removes_path_separators(self, storage: LocalStorage):
        """Test that sanitize removes path separators."""
        unsafe = "path\\to\\file.txt"
        safe = storage._sanitize_filename(unsafe)

        assert "\\" not in safe
        assert "/" not in safe
        assert "file.txt" in safe

    def test__sanitize_filename__removes_null_bytes(self, storage: LocalStorage):
        """Test that sanitize removes null bytes."""
        unsafe = "file\x00name.txt"
        safe = storage._sanitize_filename(unsafe)

        assert "\x00" not in safe
        assert "file" in safe
        assert "name.txt" in safe

    def test__sanitize_filename__limits_length(self, storage: LocalStorage):
        """Test that sanitize limits filename length to 255 characters."""
        long_name = "a" * 300 + ".txt"
        safe = storage._sanitize_filename(long_name)

        assert len(safe) <= 255
        assert safe.endswith(".txt")

    def test__sanitize_filename__preserves_valid_filenames(self, storage: LocalStorage):
        """Test that sanitize preserves valid filenames."""
        valid = "document.pdf"
        safe = storage._sanitize_filename(valid)

        assert safe == valid


class TestLocalStorageGetFilePath:
    """Tests for LocalStorage._get_file_path() method."""

    def test__get_file_path__returns_correct_structure(
        self, storage: LocalStorage, sample_project_id: UUID, sample_asset_id: UUID, sample_filename: str
    ):
        """Test that _get_file_path returns correct path structure."""
        file_path = storage._get_file_path(sample_project_id, sample_asset_id, sample_filename)

        assert str(sample_project_id) in str(file_path)
        assert str(sample_asset_id) in str(file_path)
        assert sample_filename in str(file_path)
        assert file_path.parent.parent == storage.base_path / str(sample_project_id)
        assert file_path.parent == storage.base_path / str(sample_project_id) / str(sample_asset_id)
