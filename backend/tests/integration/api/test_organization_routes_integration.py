import requests
from loguru import logger
from tests.integration.utils.test_utils import (
    get_auth_token,
    BASE_URL,
    create_organization,
    change_user_role,
    check_admin_access,
    authenticate_admin,
    get_organization_details,
)
import uuid
import pytest

pytestmark = pytest.mark.skipif(True)

# Global variables to store organization ID and request ID
organization_id = None
request_id = None


def test_create_organization():
    global organization_id  # Ensure organization_id is global
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    org_name = f"Test Organization {uuid.uuid4()}"
    response = create_organization(
        auth_headers, org_name, "TestOrgPassword123", "testorg.com"
    )

    # Log and assert the response
    logger.info(
        f"Create Organization Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 201
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()

    # Store the organization_id for use in other tests
    organization_id = response_data.get("organization_id")
    assert organization_id, "Organization ID not found in response"

    # Confirm the organization creation
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert response_data["message"] == "Organization created successfully"


def test_get_all_organizations():
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/api/organization/get-all", headers=auth_headers
    )

    logger.info(
        f"Get All Organizations Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "organizations" in response_data, f"Unexpected response: {response_data}"
    assert isinstance(
        response_data["organizations"], list
    ), "Organizations should be a list"


def test_add_admin_to_organization():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    logger.info(f"Using organization ID: {organization_id}")  # Log organization ID

    # Get auth token
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}
    logger.info(
        f"Auth token obtained: {token[:10]}..."
    )  # Log first part of the token for security

    # Log the username of the test user
    test_user_username = (
        "test_user"  # Replace with the username of the hardcoded test user
    )
    logger.info(f"Using test user username: {test_user_username}")

    # Admin details for adding admin to the organization
    admin_data = {
        "organization_id": organization_id,
        "password": "TestOrgPassword123",  # Organization's password
        "username": test_user_username,  # Username of the test user
    }

    # Send request to add the admin
    response = requests.post(
        f"{BASE_URL}/api/organization/add_admin", json=admin_data, headers=auth_headers
    )

    # Log the request body and response
    logger.info(f"Request Body: {admin_data}")  # Log the request data
    logger.info(
        f"Add Admin to Organization Response: Status Code {response.status_code}, Body {response.text}"
    )

    # Interpret the response
    if response.status_code == 400 and "User is already an admin" in response.text:
        logger.info("User is already an admin, treating as success.")
    else:
        # Assert the status code and response
        assert (
            response.status_code == 200
        ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
        response_data = response.json()
        assert "message" in response_data, f"Unexpected response: {response_data}"
        expected_message = "User has been added as an admin."
        assert (
            response_data["message"] == expected_message
        ), f"Expected message: '{expected_message}', got: '{response_data['message']}'"


def test_check_admin_access():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    check_access_data = {"organization_id": organization_id}
    response = requests.post(
        f"{BASE_URL}/api/organization/check_admin_access",
        json=check_access_data,
        headers=auth_headers,
    )

    logger.info(
        f"Check Admin Access Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
    response_data = response.json()
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert response_data["message"] == "Access granted"


def test_send_invitation():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    invite_data = {"email": "invitee@testorg.com", "organization_id": organization_id}
    response = requests.post(
        f"{BASE_URL}/api/organization/invite", json=invite_data, headers=auth_headers
    )

    logger.info(
        f"Send Invitation Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
    response_data = response.json()
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert response_data["message"] == "Invitation sent successfully"


def test_submit_join_request():
    global organization_id, request_id
    assert organization_id, "Organization ID not set from the previous test."

    # Use the hardcoded test user credentials from get_auth_token
    token, user_id = get_auth_token()  # Retrieve both token and user_id
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Submit the join request
    join_request_data = {
        "organization_id": organization_id,
        "message": "I would like to join this organization",
    }
    response = requests.post(
        f"{BASE_URL}/api/organization/join-request",
        json=join_request_data,
        headers=auth_headers,
    )

    logger.info(
        f"Submit Join Request Response: Status Code {response.status_code}, Body {response.text}"
    )

    # Ensure the request was successful
    assert (
        response.status_code == 201
    ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
    response_data = response.json()
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert (
        response_data["message"]
        == "Request to join organization submitted successfully."
    )

    # Since the response doesn't include request_id, we need to get it from pending requests
    # Get auth token for the admin user to retrieve pending requests
    admin_token, admin_user_id = get_auth_token()  # Admin user token
    admin_auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # Retrieve the pending join requests
    response = requests.get(
        f"{BASE_URL}/api/organization/pending-requests/{organization_id}",
        headers=admin_auth_headers,
    )

    logger.info(
        f"Get Pending Requests Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
    pending_requests = response.json().get("pending_requests", [])
    assert len(pending_requests) > 0, "No pending requests found."

    # Find the request made by the test user using user_id
    for req in pending_requests:
        if req["requesting_user"] == user_id:
            request_id = req["request_id"]
            break
    assert request_id, "Request ID not found for the requester."


def test_approve_join_request():
    global organization_id, request_id
    assert organization_id, "Organization ID not set from the previous test."
    assert request_id, "Request ID not set from the previous test."

    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    approve_data = {
        "request_id": request_id,
        "approve": True,
        "membershipType": "free",
        "organization_id": organization_id,
    }
    response = requests.post(
        f"{BASE_URL}/api/organization/approve-request",
        json=approve_data,
        headers=auth_headers,
    )

    logger.info(
        f"Approve Join Request Response: Status Code {response.status_code}, Body {response.text}"
    )

    # Allow both 200 (success) and 400 (user is already an admin) as valid responses
    assert response.status_code in [
        200,
        400,
    ], f"Unexpected status code: {response.status_code}, Response: {response.text}"
    response_data = response.json()

    if response.status_code == 200:
        assert "message" in response_data, f"Unexpected response: {response_data}"
        assert response_data["message"] == "Request approved successfully"
    elif response.status_code == 400:
        assert (
            response_data["message"] == "User is already an admin"
        ), f"Unexpected response: {response_data}"


def test_change_user_permissions():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    # Get auth token and user ID
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Change user role (ensure organization_id is included in the payload)
    logger.info(f"Changing user role with organization_id: {organization_id}")

    response = change_user_role(auth_headers, "test_user", "admin", organization_id)

    logger.info(
        f"Change User Role Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"


def test_check_admin_status():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    # Get auth token and user ID
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Check admin access
    response = check_admin_access(auth_headers, organization_id)
    logger.info(
        f"Check Admin Access Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert response_data["message"] == "Access granted"


def test_authenticate_admin():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    # Authenticate admin with organization ID and password
    response = authenticate_admin(organization_id, "TestOrgPassword123")
    logger.info(
        f"Authenticate Admin Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "success" in response_data, f"Unexpected response: {response_data}"
    assert response_data["success"]


def test_get_organization_details():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    # Get auth token and user ID
    token, user_id = get_auth_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get organization details
    response = get_organization_details(auth_headers, organization_id)
    logger.info(
        f"Get Organization Details Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}"
    response_data = response.json()
    assert "name" in response_data, f"Unexpected response: {response_data}"
    assert response_data["name"], "Organization name is missing from the response"


def test_cleanup_organization():
    global organization_id
    assert organization_id, "Organization ID not set from the previous test."

    # Get auth token and user ID
    token, user_id = get_auth_token()
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.delete(
        f"{BASE_URL}/api/organization/{organization_id}",
        headers=auth_headers,
        json={
            "organization_id": organization_id
        },  # Send organization_id in the body if required
    )

    logger.info(
        f"Cleanup Organization Response: Status Code {response.status_code}, Body {response.text}"
    )

    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}, Response: {response.text}"
    response_data = response.json()
    assert "message" in response_data, f"Unexpected response: {response_data}"
    assert response_data["message"] == "Organization deleted successfully"
