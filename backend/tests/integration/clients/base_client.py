"""Base test client for integration tests."""

import os
import uuid
from io import BytesIO
from loguru import logger
from flask import Flask
from typing import Dict, Any, Optional, Tuple

from models.registration_session import RegistrationSession
from models.user import User


def log_response(response, description):
    """Log response details for debugging"""
    logger.info(f"[{description}]")
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Body: {response.text}")
    return response


class BaseTestClient:
    """
    Base test client that provides high-level testing utilities with proper
    configuration handling and auth management.
    """

    def __init__(self, app: Flask, enable_rate_limits: bool = False):
        """Initialize test client with Flask app and configuration."""
        self.app = app
        with app.app_context():
            self.base_url = app.config.get("REACT_APP_BACKEND_URL")

        self.in_container = os.path.exists("/.dockerenv")
        self.test_client = app.test_client()
        self._current_user: Optional[User] = None
        self._current_headers: Optional[Dict[str, str]] = None

        # Adjust service URLs based on environment
        if self.in_container:
            self.es_host = "elasticsearch"
        else:
            self.es_host = "localhost"

    def _get_url(self, endpoint):
        """Construct full URL for endpoint"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _log_response(self, response, description):
        """Log response details for debugging"""
        return log_response(response, description)

    def get_registration_session(self, email):
        """Get registration session for email"""
        with self.app.app_context():
            return RegistrationSession.objects.get(email=email)

    def register_test_user(
        self,
        email=None,
        username=None,
        password=None,
        first_name="Test",
        last_name="User",
        bypass_email=True,
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Register a test user with optional email verification bypass.
        Returns (user_data, headers) tuple with auth headers ready to use.
        """
        unique_id = str(uuid.uuid4())
        user_data = {
            "email": email or f"{unique_id}@example.com",
            "username": username or f"test_user_{unique_id}",
            "password": password or str(uuid.uuid4()),
            "first_name": first_name,
            "last_name": last_name,
        }

        # Step 1: Initiate registration
        response = self.test_client.post(
            "/api/auth/initiate-registration",
            json={"email": user_data["email"]},
        )
        assert (
            response.status_code == 200
        ), f"Failed to initiate registration: {response.data}"

        # Step 2: Handle email verification
        if bypass_email:
            with self.app.app_context():
                session = self.get_registration_session(user_data["email"])
                session.registration_steps.email_verified = True
                session.save()

        # Step 3: Complete registration
        response = self.test_client.post("/api/auth/register", json=user_data)
        assert (
            response.status_code == 201
        ), f"Failed to complete registration: {response.data}"

        # Step 4: Login to get token
        token, refresh_token, user_id = self.get_auth_token(
            user_data["username"], user_data["password"]
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Store current user and headers for convenience
        self._current_user = User.objects.get(id=user_id)
        self._current_headers = headers

        return user_data, headers

    def get_auth_token(self, username_or_email, password):
        """Get authentication token for user. Returns (token, refresh_token, user_id)"""
        response = self.test_client.post(
            "/api/auth/login",
            json={"usernameOrEmail": username_or_email, "password": password},
        )
        self._log_response(response, "User Login")

        if response.status_code == 200:
            data = response.json
            return data["token"], data["refresh_token"], data["user"]["id"]
        raise Exception(f"Login failed: {response.data}")

    def get_current_headers(self) -> Dict[str, str]:
        """Get current auth headers, useful for test methods that need auth."""
        if not self._current_headers:
            raise ValueError(
                "No user is currently authenticated. Call register_test_user first."
            )
        return self._current_headers

    def get_current_user(self) -> User:
        """Get current user object, useful for test methods that need user data."""
        if not self._current_user:
            raise ValueError(
                "No user is currently authenticated. Call register_test_user first."
            )
        return self._current_user

    def upload_file(
        self,
        auth_headers: Dict[str, str],
        file_path: str,
        index_names: list,
        filter_dimensions: Dict[str, list],
        nominal_creator_names: Optional[list] = None,
    ):
        """Upload a file with metadata"""
        with open(file_path, "rb") as f:
            files = {"files": (file_path, BytesIO(f.read()), "application/pdf")}

        data = {
            "titles": f"test_{uuid.uuid4()}",
            "index_names": ",".join(index_names),
            "file_visibilities": '["private"]' * len(index_names),
            "nominal_creator_name": "",
            "filter_dimensions": str(filter_dimensions),
        }

        if nominal_creator_names:
            data["nominal_creator_names"] = ",".join(nominal_creator_names)

        upload_headers = auth_headers.copy()
        upload_headers.pop("Content-Type", None)

        response = self.test_client.post(
            "/api/upload", data=data, files=files, headers=upload_headers
        )
        assert response.status_code == 200, f"Upload failed: {response.data}"
        return response.json

    def delete_file(self, auth_headers: Dict[str, str], doc_id: str):
        """Delete a file"""
        response = self.test_client.delete(f"/api/file/{doc_id}", headers=auth_headers)
        assert response.status_code == 200, f"File deletion failed: {response.data}"
        return response.json

    def get_user_indices(self, auth_headers: Dict[str, str], user_id: str):
        """Get indices for a user"""
        response = self.test_client.get(
            f"/api/user/{user_id}/indices", headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get indices: {response.data}"
        return response.json

    def get_user_personal_index(self, auth_headers: Dict[str, str], user_id: str):
        """Get personal index for a user"""
        indices = self.get_user_indices(auth_headers, user_id)
        logger.info(f"Indices: {indices}")
        return indices["indices"][0]

    def create_filter_dimension(
        self, auth_headers: Dict[str, str], dimension_name: str, index_names: list
    ):
        """Create a filter dimension"""
        response = self.test_client.post(
            "/api/filter/create-filter-dimension",
            json={"dimension_name": dimension_name, "index_names": index_names},
            headers=auth_headers,
        )
        assert (
            response.status_code == 201
        ), f"Failed to create filter dimension: {response.data}"
        return response.json["dimension_id"]

    def add_value_to_filter_dimension(
        self, auth_headers: Dict[str, str], dimension_id: str, value: str
    ):
        """Add a value to a filter dimension"""
        response = self.test_client.post(
            "/api/filter/add-value-to-filter-dimension",
            json={"dimension_id": dimension_id, "value": value},
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Failed to add value: {response.data}"
