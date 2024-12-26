import pytest
from datetime import datetime, timezone

from models.file_metadata import FileMetadata
from models.pending import PendingDocument


@pytest.fixture
def test_file_metadata(test_user, test_organization, test_index_registry):
    """
    Create a test file metadata instance.

    Args:
        test_user: Test user fixture
        test_organization: Test organization fixture
        test_index_registry: Test index registry fixture

    Returns:
        FileMetadata: Created file metadata instance
    """
    metadata = FileMetadata(
        name="test_file.pdf",
        s3_url="https://test-bucket.s3.amazonaws.com/test_file.pdf",
        document_hash="test_hash_123",
        title="Test Document",
        index_names=[test_organization.index_name],
        filter_dimensions={},
        visibility="public",
        originating_user=test_user,
        organizations=[test_organization],
        index_display_name="Test Index",
        nominal_creator_name="Test Creator",
        thumbnail_urls=[
            "https://test-bucket.s3.amazonaws.com/thumbnails/test_thumb.png"
        ],
    ).save()

    yield metadata

    metadata.delete()


@pytest.fixture
def test_pending_document(test_user, test_organization):
    """
    Create a test pending document.

    Args:
        test_user: Test user fixture
        test_organization: Test organization fixture

    Returns:
        PendingDocument: Created pending document instance
    """
    pending = PendingDocument(
        name="pending_file.pdf",
        s3_url="https://test-bucket.s3.amazonaws.com/pending_file.pdf",
        document_hash="pending_hash_123",
        title="Pending Document",
        status="pending",
        organization=test_organization,
        reviewer=None,
        review_notes="",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).save()

    yield pending

    pending.delete()


def create_test_file_metadata(
    name: str = "test_file.pdf",
    user=None,
    organization=None,
    visibility: str = "public",
    **kwargs,
) -> FileMetadata:
    """
    Helper function to create test file metadata.

    Args:
        name: File name
        user: Originating user
        organization: Associated organization
        visibility: File visibility
        **kwargs: Additional metadata attributes

    Returns:
        FileMetadata: Created file metadata instance
    """
    metadata_data = {
        "name": name,
        "s3_url": kwargs.get("s3_url", f"https://test-bucket.s3.amazonaws.com/{name}"),
        "document_hash": kwargs.get(
            "document_hash", f"hash_{datetime.now().timestamp()}"
        ),
        "title": kwargs.get("title", "Test Document"),
        "index_names": kwargs.get(
            "index_names", [organization.index_name if organization else "test_index"]
        ),
        "filter_dimensions": kwargs.get("filter_dimensions", {}),
        "visibility": visibility,
        "originating_user": user,
        "organizations": [organization] if organization else [],
        "index_display_name": kwargs.get("index_display_name", "Test Index"),
        "nominal_creator_name": kwargs.get("nominal_creator_name", "Test Creator"),
        "thumbnail_urls": kwargs.get("thumbnail_urls", []),
        "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
        "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
    }

    return FileMetadata(**metadata_data).save()


def create_test_pending_document(
    name: str = "pending_file.pdf", organization=None, **kwargs
) -> PendingDocument:
    """
    Helper function to create test pending documents.

    Args:
        name: File name
        organization: Associated organization
        **kwargs: Additional document attributes

    Returns:
        PendingDocument: Created pending document instance
    """
    pending_data = {
        "name": name,
        "s3_url": kwargs.get("s3_url", f"https://test-bucket.s3.amazonaws.com/{name}"),
        "document_hash": kwargs.get(
            "document_hash", f"pending_hash_{datetime.now().timestamp()}"
        ),
        "title": kwargs.get("title", "Pending Document"),
        "status": kwargs.get("status", "pending"),
        "organization": organization,
        "review_notes": kwargs.get("review_notes", ""),
        "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
        "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
    }

    return PendingDocument(**pending_data).save()


class FileTestError(Exception):
    """Base exception for file test errors."""

    pass


class FileMetadataError(FileTestError):
    """Raised when file metadata operations fail in tests."""

    pass


class PendingDocumentError(FileTestError):
    """Raised when pending document operations fail in tests."""

    pass


# Export all needed items
__all__ = [
    "test_file_metadata",
    "test_pending_document",
    "create_test_file_metadata",
    "create_test_pending_document",
    "FileTestError",
    "FileMetadataError",
    "PendingDocumentError",
]
