import pytest
import time
from loguru import logger
from tests.integration.clients.base_client import BaseTestClient
from utils.error_handlers import log_error

# Constants for performance thresholds
MAX_UPLOAD_TIME = 60  # seconds
VERIFICATION_RETRY_DELAY = 5  # seconds
MAX_VERIFICATION_RETRIES = 10


@pytest.mark.parametrize(
    "file_path, filter_dimensions, nominal_creator_names",
    [
        (
            "tests/test_pdfs/ATLASPLAN.pdf",
            {"TestDimension1": ["Value1"], "TestDimension2": ["Value2"]},
            ["Test Org"],
        ),
        (
            "tests/test_pdfs/ATLASPLAN.pdf",
            {"TestDimension1": ["Value1"], "TestDimension2": ["Value2"]},
            None,
        ),
    ],
)
def test_file_upload_and_retrieval(
    base_test_client: BaseTestClient,
    registered_user,
    file_path,
    filter_dimensions,
    nominal_creator_names,
):
    _, auth_headers = registered_user
    user = base_test_client.get_current_user()
    try:
        # Get user's personal index
        index_name = base_test_client.get_user_personal_index(
            auth_headers, str(user.id)
        )["name"]
        index_names = [index_name]

        # Create filter dimensions and add values
        for dimension, values in filter_dimensions.items():
            dimension_id = base_test_client.create_filter_dimension(
                auth_headers, dimension, index_names
            )
            for value in values:
                base_test_client.add_value_to_filter_dimension(
                    auth_headers, dimension_id, value
                )

        # Upload a test file
        start_time = time.time()
        upload_response = base_test_client.upload_file(
            auth_headers,
            file_path,
            index_names,
            filter_dimensions,
            nominal_creator_names,
        )
        upload_time = time.time() - start_time
        assert (
            upload_time < MAX_UPLOAD_TIME
        ), f"Upload took too long: {upload_time} seconds"

        file_id = upload_response["doc_id"]
        logger.info(f"File uploaded successfully. File ID: {file_id}")

        # Add a delay before verification
        time.sleep(VERIFICATION_RETRY_DELAY)

        # Verify the file's presence in the system with retries
        for attempt in range(MAX_VERIFICATION_RETRIES):
            verify_response = base_test_client.test_client.get(
                f"/api/file/{file_id}", headers=auth_headers
            )
            logger.info(
                f"Verification attempt {attempt + 1}: Status {verify_response.status_code}, Response: {verify_response.data}"
            )
            if verify_response.status_code == 200:
                break
            logger.warning(
                f"File verification attempt {attempt + 1} failed. Retrying in {VERIFICATION_RETRY_DELAY} seconds..."
            )
            time.sleep(VERIFICATION_RETRY_DELAY)

        assert (
            verify_response.status_code == 200
        ), f"File verification failed after {MAX_VERIFICATION_RETRIES} attempts. Final status: {verify_response.status_code}, Response: {verify_response.data}"

        verify_data = verify_response.json
        logger.info(f"File verification successful. Response: {verify_data}")

        # Check the structure and content of the response
        assert "doc_id" in verify_data
        assert verify_data["doc_id"] == file_id
        assert "title" in verify_data
        assert verify_data["title"].startswith("test_")
        assert "visibility" in verify_data
        assert verify_data["visibility"] == "private"
        assert "s3_url" in verify_data
        assert "index_names" in verify_data
        assert isinstance(verify_data["index_names"], list)
        assert index_name in verify_data["index_names"]
        assert "thumbnail_urls" in verify_data
        assert isinstance(verify_data["thumbnail_urls"], list)
        assert "filter_dimensions" in verify_data
        assert isinstance(verify_data["filter_dimensions"], dict)
        assert verify_data["filter_dimensions"] == filter_dimensions
        assert "index_display_name" in verify_data
        if nominal_creator_names:
            assert verify_data["index_display_name"] == nominal_creator_names[0]
        else:
            assert "nominal_creator_name" in verify_data

    except Exception as e:
        log_error(e, "Test failed with error")
        raise

    finally:
        # Clean up
        if "file_id" in locals():
            delete_response = base_test_client.delete_file(auth_headers, file_id)
            assert (
                delete_response["message"]
                == "Document deleted successfully from all specified indices"
            ), f"Failed to delete file: {delete_response}"


@pytest.mark.parametrize(
    "file_path, filter_dimensions, nominal_creator_names",
    [
        (
            "tests/test_pdfs/CONQUEST_BROCHURE.pdf",
            {"TestDimension1": ["Value1"], "TestDimension2": ["Value2"]},
            ["Test Org"],
        ),
        (
            "tests/test_pdfs/CONQUEST_BROCHURE.pdf",
            {"TestDimension1": ["Value1"], "TestDimension2": ["Value2"]},
            None,
        ),
    ],
)
def test_file_upload_and_retrieval_2(
    base_test_client: BaseTestClient,
    registered_user,
    file_path,
    filter_dimensions,
    nominal_creator_names,
):
    _, auth_headers = registered_user
    user = base_test_client.get_current_user()
    try:
        # Get user's personal index
        index_name = base_test_client.get_user_personal_index(
            auth_headers, str(user.id)
        )["name"]
        index_names = [index_name]

        # Create filter dimensions and add values
        for dimension, values in filter_dimensions.items():
            dimension_id = base_test_client.create_filter_dimension(
                auth_headers, dimension, index_names
            )
            for value in values:
                base_test_client.add_value_to_filter_dimension(
                    auth_headers, dimension_id, value
                )

        # Upload a test file
        start_time = time.time()
        upload_response = base_test_client.upload_file(
            auth_headers,
            file_path,
            index_names,
            filter_dimensions,
            nominal_creator_names,
        )
        upload_time = time.time() - start_time
        assert (
            upload_time < MAX_UPLOAD_TIME
        ), f"Upload took too long: {upload_time} seconds"

        file_id = upload_response["doc_id"]
        logger.info(f"File uploaded successfully. File ID: {file_id}")

        # Add a delay before verification
        time.sleep(VERIFICATION_RETRY_DELAY)

        # Verify the file's presence in the system with retries
        for attempt in range(MAX_VERIFICATION_RETRIES):
            verify_response = base_test_client.test_client.get(
                f"/api/file/{file_id}", headers=auth_headers
            )
            logger.info(
                f"Verification attempt {attempt + 1}: Status {verify_response.status_code}, Response: {verify_response.data}"
            )
            if verify_response.status_code == 200:
                break
            logger.warning(
                f"File verification attempt {attempt + 1} failed. Retrying in {VERIFICATION_RETRY_DELAY} seconds..."
            )
            time.sleep(VERIFICATION_RETRY_DELAY)

        assert (
            verify_response.status_code == 200
        ), f"File verification failed after {MAX_VERIFICATION_RETRIES} attempts. Final status: {verify_response.status_code}, Response: {verify_response.data}"

        verify_data = verify_response.json
        logger.info(f"File verification successful. Response: {verify_data}")

        # Check the structure and content of the response
        assert "doc_id" in verify_data
        assert verify_data["doc_id"] == file_id
        assert "title" in verify_data
        assert verify_data["title"].startswith("test_")
        assert "visibility" in verify_data
        assert verify_data["visibility"] == "private"
        assert "s3_url" in verify_data
        assert "index_names" in verify_data
        assert isinstance(verify_data["index_names"], list)
        assert index_name in verify_data["index_names"]
        assert "thumbnail_urls" in verify_data
        assert isinstance(verify_data["thumbnail_urls"], list)
        assert "filter_dimensions" in verify_data
        assert isinstance(verify_data["filter_dimensions"], dict)
        assert verify_data["filter_dimensions"] == filter_dimensions
        assert "index_display_name" in verify_data
        if nominal_creator_names:
            assert verify_data["nominal_creator_name"] == nominal_creator_names[0]
        else:
            assert "nominal_creator_name" in verify_data

    except Exception as e:
        log_error(e, "Test failed with error")
        raise

    finally:
        # Clean up
        if "file_id" in locals():
            delete_response = base_test_client.delete_file(auth_headers, file_id)
            assert (
                delete_response["message"]
                == "Document deleted successfully from all specified indices"
            ), f"Failed to delete file: {delete_response}"


def test_file_deletion(base_test_client: BaseTestClient, registered_user):
    _, auth_headers = registered_user
    user = base_test_client.get_current_user()
    # Get user's personal index
    index_name = base_test_client.get_user_personal_index(auth_headers, str(user.id))[
        "name"
    ]
    index_names = [index_name]

    # Use an actual test file in your project
    file_path = "tests/test_pdfs/ATLASPLAN.pdf"
    filter_dimensions = {}  # No filter dimensions for this test
    nominal_creator_names = (
        None  # Test without providing a nominal creator org display name
    )

    try:
        # Upload the file
        upload_response = base_test_client.upload_file(
            auth_headers,
            file_path,
            index_names,
            filter_dimensions,
            nominal_creator_names,
        )
        file_id = upload_response["doc_id"]

        # Add a delay before verification
        time.sleep(VERIFICATION_RETRY_DELAY)

        # Verify the file's presence with retries
        for attempt in range(MAX_VERIFICATION_RETRIES):
            verify_response = base_test_client.test_client.get(
                f"/api/file/{file_id}", headers=auth_headers
            )
            logger.info(
                f"Verification attempt {attempt + 1}: Status {verify_response.status_code}, Response: {verify_response.data}"
            )
            if verify_response.status_code == 200:
                break
            logger.warning(
                f"File verification attempt {attempt + 1} failed. Retrying in {VERIFICATION_RETRY_DELAY} seconds..."
            )
            time.sleep(VERIFICATION_RETRY_DELAY)

        assert (
            verify_response.status_code == 200
        ), f"File verification failed after {MAX_VERIFICATION_RETRIES} attempts. Final status: {verify_response.status_code}, Response: {verify_response.data}"

        # Delete the file
        delete_response = base_test_client.delete_file(auth_headers, file_id)
        assert (
            delete_response["message"]
            == "Document deleted successfully from all specified indices"
        ), f"Failed to delete file: {delete_response}"

        # Wait for a short time to allow for any asynchronous processes to complete
        time.sleep(VERIFICATION_RETRY_DELAY)

        # Verify that the file has been soft-deleted
        delete_verify_response = base_test_client.test_client.get(
            f"/api/file/{file_id}", headers=auth_headers
        )
        assert (
            delete_verify_response.status_code == 404
        ), f"File was not deleted as expected. Status: {delete_verify_response.status_code}, Response: {delete_verify_response.data}"

    except Exception as e:
        log_error(e, "Test failed with error")
        raise


if __name__ == "__main__":
    pytest.main([__file__])
