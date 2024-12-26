import pytest
import requests
from loguru import logger
from flask import current_app
import uuid
from tests.integration.utils.test_utils import test_client

BASE_URL = current_app.config.get("REACT_APP_BACKEND_URL")


# Helper function to log responses
def log_response(response, description):
    logger.info(f"[{description}]")
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Body: {response.text}")


@pytest.fixture(scope="module")
def dynamic_user():
    """
    Fixture to generate a dynamic user for testing.
    """
    unique_id = str(uuid.uuid4())  # Generate a unique identifier
    dynamic_user_data = {
        "email": f"test_user_{unique_id}@example.com",
        "username": f"test_user_{unique_id}",
        "password": "7AoMn4*g#uL$Lt",
        "first_name": "Test",
        "last_name": "User",
    }
    yield dynamic_user_data  # Provide the dynamic user data for the test
    # Cleanup: After the tests, delete the dynamic user if it exists
    try:
        token, refresh_token, user_id = test_client.get_auth_token(
            dynamic_user_data["username"], dynamic_user_data["password"]
        )
        auth_headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(
            f"{BASE_URL}/api/user/{user_id}", headers=auth_headers
        )
        log_response(response, f"Delete Dynamic User {dynamic_user_data['username']}")
    except Exception as e:
        logger.error(f"Failed to delete dynamic user: {str(e)}")


# Test fetching user indices
def test_get_user_indices():
    """
    Test fetching user indices for the test user.
    """
    # Get auth token and user ID using the test user from integration utils
    token, refresh_token, user_id = test_client.get_auth_token()

    # Prepare the request headers with the token
    headers = {"Authorization": f"Bearer {token}"}

    # Make the request to get user indices
    response = requests.get(f"{BASE_URL}/api/user/{user_id}/indices", headers=headers)
    log_response(response, "Get User Indices")

    # Assert the status code and response
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "personal_index" in response_data, "No personal index found in response"
    assert (
        "organization_indices" in response_data
    ), "No organization indices found in response"


# Test fetching user organizations
def test_get_user_organizations():
    """
    Test fetching user organizations for the test user.
    """
    # Get auth token and user ID using the test user from integration utils
    token, refresh_token, user_id = test_client.get_auth_token()

    # Prepare the request headers with the token
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Make the request to get user organizations
    response = requests.get(
        f"{BASE_URL}/api/user/{user_id}/organizations", headers=auth_headers
    )
    log_response(response, "Get User Organizations")

    # Assert the status code and response
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "organizations" in response_data, "No 'organizations' found in response"


# Test fetching user roles
def test_get_user_roles():
    """
    Test fetching user roles for the test user.
    """
    # Get auth token and user ID using the test user from integration utils
    token, refresh_token, user_id = test_client.get_auth_token()

    # Prepare the request headers with the token
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Make the request to get user roles
    response = requests.get(
        f"{BASE_URL}/api/user/{user_id}/roles", headers=auth_headers
    )
    log_response(response, "Get User Roles")

    # Assert the status code and response
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "roles" in response_data, "No 'roles' found in response"
