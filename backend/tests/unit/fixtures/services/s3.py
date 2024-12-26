import os
import pytest
from unittest.mock import MagicMock
from typing import Generator, Any
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def mock_s3_service():
    """
    Centralized mock S3 service for testing file operations.
    Used by both file routes and document petition tests.

    Returns:
        MagicMock: Configured S3 service mock
    """
    mock = MagicMock()

    # Configure standard S3 operations
    mock.upload_file_to_s3.return_value = (
        "https://test-bucket.s3.amazonaws.com/test.pdf"
    )
    mock.extract_s3_key.return_value = "test.pdf"

    # Configure multipart upload operations
    mock.create_multipart_upload.return_value = {
        "UploadId": "test-upload-id",
        "Key": "test.pdf",
    }
    mock.complete_multipart_upload.return_value = {
        "Location": "https://test-bucket.s3.amazonaws.com/test.pdf",
        "Key": "test.pdf",
        "ETag": "test-etag",
    }

    # Configure S3 client operations
    mock.s3_client = MagicMock()
    mock.s3_client.download_file = MagicMock()
    mock.s3_client.upload_file = MagicMock()
    mock.s3_client.delete_object = MagicMock()
    mock.s3_client.head_object = MagicMock(
        return_value={
            "ContentLength": 1024,
            "ContentType": "application/pdf",
            "LastModified": "2024-01-01 00:00:00",
        }
    )

    # Configure presigned URL operations
    mock.generate_presigned_url.return_value = (
        "https://test-bucket.s3.amazonaws.com/presigned-test.pdf"
    )
    mock.generate_presigned_post.return_value = {
        "url": "https://test-bucket.s3.amazonaws.com",
        "fields": {
            "key": "test.pdf",
            "AWSAccessKeyId": "test-key",
            "policy": "test-policy",
            "signature": "test-signature",
        },
    }

    return mock


@pytest.fixture(scope="session")
def test_files_dir(tmp_path_factory) -> Generator[str, Any, None]:
    """
    Create and manage a temporary directory for test files.
    Session-scoped to maintain files across tests.

    Yields:
        str: Path to temporary test directory
    """
    test_dir = tmp_path_factory.mktemp("test_files")
    yield str(test_dir)
    # Cleanup handled automatically by pytest


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for file uploads during tests.

    Yields:
        Path: Path to temporary upload directory
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf_file(test_files_dir) -> Generator[str, None, None]:
    """
    Create a sample PDF file for testing.

    Args:
        test_files_dir: Directory for test files

    Yields:
        str: Path to sample PDF file
    """
    pdf_content = b"%PDF-1.4\n%Test PDF content"
    pdf_path = os.path.join(test_files_dir, "sample.pdf")

    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    yield pdf_path

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.fixture
def large_file_upload_response() -> dict:
    """
    Fixture providing a standard response for large file upload initiation.

    Returns:
        dict: Mock response for large file upload
    """
    return {
        "uploadId": "test-upload-id",
        "key": "test-large-file.pdf",
        "parts": [
            {
                "PartNumber": 1,
                "PresignedUrl": "https://test-bucket.s3.amazonaws.com/part1",
            },
            {
                "PartNumber": 2,
                "PresignedUrl": "https://test-bucket.s3.amazonaws.com/part2",
            },
        ],
    }


def create_test_file(
    directory: str, filename: str, content: bytes = b"test content"
) -> str:
    """
    Create a test file with specified content.

    Args:
        directory: Directory to create file in
        filename: Name of the file
        content: File content in bytes

    Returns:
        str: Path to created file
    """
    file_path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def configure_s3_mock_error(
    mock_service: MagicMock, operation: str, error_code: str = "Error"
) -> None:
    """
    Configure an S3 mock to raise an error for specific operation.

    Args:
        mock_service: The S3 service mock
        operation: Operation to raise error for
        error_code: AWS error code to simulate
    """

    class S3Error(Exception):
        pass

    error = S3Error()
    error.response = {"Error": {"Code": error_code}}

    getattr(mock_service, operation).side_effect = error


# Custom exceptions for S3 testing
class S3UploadError(Exception):
    """Raised when S3 upload fails in tests."""

    pass


class S3DownloadError(Exception):
    """Raised when S3 download fails in tests."""

    pass


# Export all needed items
__all__ = [
    "mock_s3_service",
    "test_files_dir",
    "temp_upload_dir",
    "sample_pdf_file",
    "large_file_upload_response",
    "create_test_file",
    "configure_s3_mock_error",
    "S3UploadError",
    "S3DownloadError",
]
