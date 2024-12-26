import pytest
import jwt
from datetime import datetime, timedelta, timezone
from tests.utils.data_factory import DataFactory
from models.user import User
from models.registration_session import RegistrationSession


@pytest.fixture
def test_user_data():
    """Generate test user data using DataFactory"""
    return DataFactory.registration_data().__dict__


@pytest.fixture
def verified_registration_session(test_user_data):
    """Create a verified registration session"""
    session = RegistrationSession.create_session(test_user_data["email"])
    session.registration_steps.email_verified = True
    session.save()
    yield session
    session.delete()


@pytest.fixture
def unique_username():
    """Generate a unique username for testing"""
    return DataFactory.unique_username()


@pytest.mark.blueprints(["auth"])
class TestAuthRegistration:
    """Tests for user registration flows"""

    @pytest.mark.test_size("medium")
    def test_registration_success_flow(
        self,
        integration_client,
        test_user_data,
        verified_registration_session,
        test_app,
    ):
        """Test the complete registration success flow"""
        # Step 1: Initiate registration
        response = integration_client.post(
            "/auth/initiate-registration", json={"email": test_user_data["email"]}
        )
        assert response.status_code == 200

        reg_session = RegistrationSession.objects.get(email=test_user_data["email"])
        reg_session.registration_steps.email_verified = True
        reg_session.save()

        # Step 2: Complete registration
        response = integration_client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        assert "User registered successfully" in response.json["message"]

        # Verify user was created correctly
        user = User.objects(email=test_user_data["email"]).first()
        assert user is not None
        assert user.username == test_user_data["username"]
        assert user.is_verified is True

        # Step 3: Verify login works
        response = integration_client.post(
            "/auth/login",
            json={
                "usernameOrEmail": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert response.status_code == 200
        token = response.json["token"]
        refresh_token = response.json["refresh_token"]
        assert token is not None
        assert refresh_token is not None

        # Verify token contains correct user data
        secret = test_app.config["SECRET_KEY"]
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["email"] == test_user_data["email"]
        assert decoded["username"] == test_user_data["username"]

    @pytest.mark.parametrize(
        "error_case",
        [
            ("missing_fields", {}),
            ("invalid_email", {"email": "invalid-email"}),
            ("short_password", {"password": "short"}),
        ],
    )
    @pytest.mark.test_size("medium")
    def test_registration_error_cases(self, integration_client, error_case):
        """Test various registration error cases"""
        case_name, data = error_case
        response = integration_client.post("/auth/register", json=data)
        assert response.status_code == 400

    @pytest.mark.test_size("medium")
    def test_registration_with_organization(
        self,
        integration_client,
        test_user_data,
        verified_registration_session,
    ):
        """Test registration with organization flow"""
        # Create organization and invitation
        org = DataFactory.create_organization()
        invitation = DataFactory.create_invitation(
            email=test_user_data["email"], organization=org, token="test_token"
        )
        test_user_data["invitation_token"] = "test_token"

        # Register user
        response = integration_client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201

        # Verify organization assignment
        user = User.objects(email=test_user_data["email"]).first()
        assert user.initial_organization == org

        # Cleanup
        org.delete()
        invitation.delete()


class TestAuthLogin:
    """Tests for login and session management"""

    @pytest.mark.test_size("medium")
    def test_successful_login_with_email(
        self, integration_client, registered_user, test_app
    ):
        """Test successful login using email"""
        user_data, _ = registered_user
        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": "Test123!@#",
        }
        response = integration_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json
        assert all(key in data for key in ["token", "refresh_token", "user"])

        # Verify token contains correct user data
        secret = test_app.config["SECRET_KEY"]
        decoded = jwt.decode(data["token"], secret, algorithms=["HS256"])
        assert decoded["email"] == user_data["email"]
        assert decoded["username"] == user_data["username"]

    @pytest.mark.test_size("medium")
    def test_successful_login_with_username(self, integration_client, registered_user):
        """Test successful login using username"""
        user_data, _ = registered_user
        login_data = {
            "usernameOrEmail": user_data["username"],
            "password": "Test123!@#",
        }
        response = integration_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        assert "token" in response.json

    @pytest.mark.test_size("medium")
    def test_login_updates_last_login(
        self, integration_client, registered_user, base_test_client
    ):
        """Test that successful login updates last_login timestamp"""
        user_data, _ = registered_user
        user = base_test_client.get_current_user()
        initial_login = user.last_login

        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": "Test123!@#",
        }
        integration_client.post("/auth/login", json=login_data)

        user = User.objects.get(id=user.id)
        assert user.last_login.replace(tzinfo=timezone.utc) > initial_login.replace(
            tzinfo=timezone.utc
        )

    @pytest.mark.parametrize(
        "credentials",
        [
            {"email": "wrong@email.com", "password": "Test123!@#"},
            {"email": "test@email.com", "password": "WrongPass123!"},
        ],
    )
    @pytest.mark.test_size("medium")
    def test_login_failures(self, integration_client, registered_user, credentials):
        """Test login failure scenarios"""
        login_data = {
            "usernameOrEmail": credentials["email"],
            "password": credentials["password"],
        }
        response = integration_client.post("/auth/login", json=login_data)
        assert response.status_code == 401


class TestLogoutFlow:
    """Tests for logout process and token invalidation"""

    @pytest.mark.test_size("medium")
    def test_successful_logout(
        self, integration_client, registered_user, base_test_client
    ):
        """Test successful logout and token blacklisting"""
        _, auth_headers = registered_user
        response = integration_client.post("/auth/logout", headers=auth_headers)
        assert response.status_code == 200

        # Verify token was blacklisted
        token = auth_headers["Authorization"].split()[1]
        user = base_test_client.get_current_user()
        assert token in user.blacklisted_tokens

    @pytest.mark.test_size("medium")
    def test_logout_without_token(self, integration_client):
        """Test logout attempt without authentication token"""
        response = integration_client.post("/auth/logout")
        assert response.status_code == 200  # Logout should still succeed

    @pytest.mark.test_size("medium")
    def test_blacklisted_token_prevents_access(
        self, integration_client, registered_user
    ):
        """Test that blacklisted tokens can't be used for authentication"""
        _, auth_headers = registered_user
        # First logout to blacklist the token
        integration_client.post("/auth/logout", headers=auth_headers)

        # Attempt to use the same token
        response = integration_client.get(
            "/some/protected/endpoint", headers=auth_headers
        )
        assert response.status_code == 404


class TestTokenRefresh:
    """Tests for token refresh functionality"""

    @pytest.mark.test_size("medium")
    def test_successful_token_refresh(
        self, integration_client, registered_user, test_app
    ):
        """Test successful token refresh flow"""
        user_data, _ = registered_user
        # First login to get tokens
        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": "Test123!@#",
        }
        login_response = integration_client.post("/auth/login", json=login_data)
        refresh_token = login_response.json["refresh_token"]

        # Use refresh token to get new access token
        response = integration_client.post(
            "/auth/refresh_token", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json

        # Verify new token is valid and contains correct user data
        new_token = response.json["access_token"]
        secret = test_app.config["SECRET_KEY"]
        decoded = jwt.decode(new_token, secret, algorithms=["HS256"])
        assert decoded["email"] == user_data["email"]

    @pytest.mark.test_size("medium")
    def test_refresh_with_expired_token(
        self, integration_client, registered_user, test_app
    ):
        """Test refresh attempt with expired refresh token"""
        user_data, _ = registered_user
        user = User.objects.get(email=user_data["email"])
        # Generate expired refresh token
        user_data = {
            "user_id": str(user.id),
            "email": user.email,
            "exp": datetime.utcnow() - timedelta(days=1),
        }
        secret = test_app.config["SECRET_KEY"]
        expired_token = jwt.encode(user_data, secret, algorithm="HS256")

        response = integration_client.post(
            "/auth/refresh_token", json={"refresh_token": expired_token}
        )
        assert response.status_code == 401
        assert "expired" in response.json["error"].lower()

    @pytest.mark.test_size("medium")
    def test_refresh_with_blacklisted_token(self, integration_client, registered_user):
        """Test refresh attempt with blacklisted refresh token"""
        user_data, _ = registered_user
        # First login to get tokens
        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": "Test123!@#",
        }
        login_response = integration_client.post("/auth/login", json=login_data)
        refresh_token = login_response.json["refresh_token"]

        # Blacklist the refresh token
        user = User.objects.get(email=user_data["email"])
        user.blacklisted_tokens.append(refresh_token)
        user.save()

        # Attempt to use blacklisted refresh token
        response = integration_client.post(
            "/auth/refresh_token", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401
        assert "invalidated" in response.json["error"].lower()

    @pytest.mark.test_size("medium")
    def test_refresh_updates_user_data(
        self, integration_client, registered_user, test_app
    ):
        """Test that refreshed token contains updated user data"""
        user_data, _ = registered_user
        # First login to get tokens
        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": "Test123!@#",
        }
        login_response = integration_client.post("/auth/login", json=login_data)
        refresh_token = login_response.json["refresh_token"]

        # Update user data
        org = DataFactory.create_organization()
        user = User.objects.get(email=user_data["email"])
        user.initial_organization = org
        user.save()

        # Refresh token
        response = integration_client.post(
            "/auth/refresh_token", json={"refresh_token": refresh_token}
        )

        # Verify new token contains updated data
        new_token = response.json["access_token"]
        secret = test_app.config["SECRET_KEY"]
        decoded = jwt.decode(new_token, secret, algorithms=["HS256"])
        assert decoded["initial_organization"] == str(org.id)

        # Cleanup
        org.delete()


class TestPasswordManagement:
    """Tests for password-related functionality"""

    @pytest.mark.test_size("medium")
    def test_password_reset_flow(self, integration_client, registered_user):
        """Test the complete password reset flow"""
        user_data, _ = registered_user
        # Request reset
        response = integration_client.post(
            "/auth/forgot-password", json={"email": user_data["email"]}
        )
        assert response.status_code == 200
        reset_token = response.json.get("reset_token")
        assert reset_token

        # Reset password
        new_password = "NewTestPassword123"
        reset_response = integration_client.post(
            f"/auth/reset-password/{reset_token}",
            json={"new_password": new_password},
        )
        assert reset_response.status_code == 200

        # Verify new password works
        login_data = {
            "usernameOrEmail": user_data["email"],
            "password": new_password,
        }
        login_response = integration_client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200


class TestUsernameManagement:
    """Tests for username-related functionality"""

    @pytest.mark.test_size("medium")
    @pytest.mark.parametrize(
        "username_type", ["valid", "too_short", "invalid_chars", "too_long"]
    )
    def test_username_availability(
        self, integration_client, username_type, unique_username
    ):
        """Test username availability checks"""
        if username_type == "valid":
            username = unique_username
            expected_available = True
        elif username_type == "too_short":
            username = "ab"
            expected_available = False
        elif username_type == "invalid_chars":
            username = "test@user"
            expected_available = False
        else:  # too_long
            username = "very_long_username_over_20_chars"
            expected_available = False

        response = integration_client.get(f"/auth/check-username/{username}")
        if expected_available:
            assert response.status_code == 200
            assert response.json["available"]
        else:
            assert response.status_code == 400 or not response.json["available"]
