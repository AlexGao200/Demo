import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
import jwt

from services.auth_service import (
    AuthService,
    LoginData,
    RegistrationError,
    UserExistsError,
    LoginError,
    TokenError,
    AuthError,
)

from models.user import User
from models.registration_session import RegistrationSession, RegistrationSteps
from models.invitation import Invitation
from models.user_organization import UserOrganization
from tests.utils.data_factory import DataFactory
import uuid
from tests.unit.fixtures import create_minimal_app


@pytest.fixture
def email_service():
    """Mock email service as it's an external dependency"""
    mock = Mock()
    mock.send_verification_email.return_value = True
    mock.send.return_value = True
    return mock


@pytest.fixture
def app():
    """Create Flask app for tests requiring application context"""
    return create_minimal_app(["auth"])  # Use the minimal app with auth blueprint


@pytest.fixture
def auth_service(email_service, app, user_service):  # Added user_service dependency
    """Create AuthService instance with test configuration"""
    with app.app_context():
        return AuthService(email_service, app.config["SECRET_KEY"], user_service)


class TestEmailValidation:
    """Unit tests for email validation logic"""

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("valid@example.com", True),
            ("valid+label@example.com", True),
            ("valid.name@example.co.uk", True),
            ("invalid@", False),
            ("invalid", False),
            ("invalid@.com", False),
            ("@invalid.com", False),
        ],
    )
    def test_email_validation(self, auth_service, email, expected):
        assert auth_service.is_valid_email(email) == expected


class TestRegistrationFlow:
    """Tests for registration flow using real database"""

    def test_initiate_registration_invalid_email(self, auth_service: AuthService):
        """Test registration fails with invalid email format"""
        with pytest.raises(RegistrationError, match="Invalid email format"):
            auth_service.initiate_registration("invalid_email")

    def test_initiate_registration_existing_user(self, auth_service: AuthService):
        """Test registration fails for existing user using real database"""
        user = DataFactory.create_user()

        with pytest.raises(UserExistsError, match="Email already registered"):
            auth_service.initiate_registration(user.email)

    def test_initiate_registration_success(self, auth_service: AuthService):
        """Test successful registration initiation with database verification"""
        email = DataFactory.get_unique_email()

        # Create user first to avoid query error
        DataFactory.create_user(email=email, save=False)

        auth_service.initiate_registration(email)

        # Verify registration session was created in database
        session = RegistrationSession.objects(email=email).first()
        assert session is not None
        assert session.verification_code is not None
        auth_service.email_service.send_verification_email.assert_called_once()

    def test_verify_email_with_code_success(self, auth_service: AuthService):
        """Test successful email verification using database"""
        email = DataFactory.get_unique_email()
        verification_code = "123456"

        # Create registration session with registration_steps
        session = RegistrationSession(
            email=email,
            verification_code=verification_code,
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=False),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        assert auth_service.verify_email_with_code(email, verification_code)

        # Verify session was updated in database
        session.reload()
        assert session.registration_steps.email_verified

    def test_verify_email_code_invalid(self, auth_service: AuthService):
        """Test verification fails with invalid code"""
        email = DataFactory.get_unique_email()
        RegistrationSession(
            email=email,
            verification_code="123456",
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=False),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        with pytest.raises(Exception):
            auth_service.verify_email_with_code(email, "invalid")

    def test_complete_registration_basic(self, auth_service: AuthService):
        """Test basic registration completion with database verification"""
        email = DataFactory.get_unique_email()
        RegistrationSession(
            email=email,
            verification_code="123456",
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=True),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        registration_data = DataFactory.registration_data(email=email)
        user, org_name = auth_service.complete_registration(registration_data)

        assert user is not None
        assert org_name is None

        db_user = User.objects(email=email).first()
        assert db_user is not None
        assert db_user.is_verified
        assert db_user.email == email
        assert db_user.username == registration_data.username

        assert RegistrationSession.objects(email=email).first() is None

    def test_complete_registration_with_invitation(self, auth_service: AuthService):
        """Test registration with organization invitation using database"""
        org = DataFactory.create_organization()
        email = DataFactory.get_unique_email()
        invitation_token = f"test_invitation_{uuid.uuid4().hex}"

        # Create invitation with sent_at instead of created_at
        invitation = Invitation(
            email=email,
            organization=org,
            token=invitation_token,
            accepted=False,
            sent_at=datetime.now(timezone.utc),
        ).save()

        RegistrationSession(
            email=email,
            verification_code="123456",
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=True),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        registration_data = DataFactory.registration_data(
            email=email,
            invitation_token=invitation_token,  # Use same unique token
        )
        user, org_name = auth_service.complete_registration(registration_data)

        assert user is not None
        assert org_name == org.name

        db_user = User.objects(id=user.id).first()
        assert db_user is not None
        assert db_user.initial_organization == org

        user_org = UserOrganization.objects(user=user, organization=org).first()
        assert user_org is not None
        assert user_org.role == "member"

        invitation.reload()
        assert invitation.accepted

    def test_complete_registration_unverified_email(self, auth_service: AuthService):
        """Test registration fails with unverified email"""
        email = DataFactory.get_unique_email()

        # Create unverified registration session
        RegistrationSession(
            email=email,
            verification_code="123456",
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=False),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        registration_data = DataFactory.registration_data(email=email)

        with pytest.raises(RegistrationError, match="Email not verified"):
            auth_service.complete_registration(registration_data)

    def test_complete_registration_existing_email(self, auth_service: AuthService):
        """Test registration fails with existing email"""
        existing_user = DataFactory.create_user()

        RegistrationSession(
            email=existing_user.email,
            verification_code="123456",
            created_at=datetime.now(timezone.utc),
            registration_steps=RegistrationSteps(email_verified=True),
            verification_attempt_expiry=datetime.now(timezone.utc) + timedelta(days=1),
        ).save()

        registration_data = DataFactory.registration_data(email=existing_user.email)

        with pytest.raises(RegistrationError):
            auth_service.complete_registration(registration_data)


class TestUsernameValidation:
    """Tests for username validation using database"""

    @pytest.mark.parametrize(
        "username,valid",
        [
            ("validuser", True),
            ("valid_user", True),
            ("valid-user", True),
            ("va", False),  # Too short
            ("a" * 21, False),  # Too long
            ("invalid@user", False),  # Invalid character
            ("invalid user", False),  # Space not allowed
        ],
    )
    def test_username_format_validation(self, auth_service, username, valid):
        result, _ = auth_service.validate_username(username)
        assert result == valid

    def test_existing_username_validation(self, auth_service: AuthService):
        """Test username validation with existing user in database"""
        # Create user with known username
        existing_user = DataFactory.create_user()

        result, message = auth_service.validate_username(existing_user.username)
        assert not result
        assert "already taken" in message.lower()


class TestLoginFlow:
    """Tests for login flow using real database"""

    def test_login_success_with_email(self, auth_service: AuthService):
        """Test successful login with email"""
        password = "Test123!@#"
        user = DataFactory.create_user(password=password)

        login_data = DataFactory.login_data(
            email_or_username=user.email, password=password
        )
        logged_in_user, tokens = auth_service.login(login_data)

        assert logged_in_user is not None
        assert tokens["access_token"] is not None
        assert tokens["refresh_token"] is not None

    def test_login_success_with_username(self, auth_service: AuthService):
        """Test successful login with username"""
        password = "Test123!@#"
        user = DataFactory.create_user(password=password)

        login_data = DataFactory.login_data(
            email_or_username=user.username, password=password
        )
        logged_in_user, tokens = auth_service.login(login_data)

        assert logged_in_user is not None
        assert tokens["access_token"] is not None
        assert tokens["refresh_token"] is not None

    def test_login_invalid_credentials(self, auth_service: AuthService):
        """Test login fails with invalid credentials"""
        user = DataFactory.create_user(password="correct_password")

        login_data = DataFactory.login_data(
            email_or_username=user.email, password="wrong_password"
        )
        with pytest.raises(LoginError):
            auth_service.login(login_data)

    def test_login_unverified_user(self, auth_service: AuthService):
        """Test login fails for unverified user"""
        password = "Test123!@#"
        user = DataFactory.create_user(password=password, is_verified=False)

        login_data = DataFactory.login_data(
            email_or_username=user.email, password=password
        )
        with pytest.raises(LoginError):
            auth_service.login(login_data)

    def test_login_nonexistent_user(self, auth_service: AuthService):
        """Test login fails for nonexistent user"""
        login_data = DataFactory.login_data()
        with pytest.raises(LoginError):
            auth_service.login(login_data)

    def test_verify_token_success(self, auth_service: AuthService):
        """Test successful token verification"""
        user = DataFactory.create_user()
        token = auth_service._generate_token(
            {"id": str(user.id), "user_id": str(user.id)}
        )

        decoded_token = jwt.decode(token, auth_service.secret_key, algorithms=["HS256"])
        assert decoded_token["user_id"] == str(user.id)

    def test_verify_token_expired(self, auth_service: AuthService):
        """Test token verification fails for expired token"""
        user = DataFactory.create_user()

        # Create token that's already expired
        payload = {
            "id": str(user.id),
            "user_id": str(user.id),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, auth_service.secret_key, algorithms=["HS256"])

    def test_verify_token_invalid(self, auth_service: AuthService):
        """Test token verification fails for invalid token"""
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode("invalid_token", auth_service.secret_key, algorithms=["HS256"])

    def test_verify_token_user_deleted(self, auth_service: AuthService):
        """Test token verification fails for deleted user"""
        user = DataFactory.create_user()
        token = auth_service._generate_token(
            {"id": str(user.id), "user_id": str(user.id)}
        )

        # Delete the user
        user.delete()

        decoded_token = jwt.decode(token, auth_service.secret_key, algorithms=["HS256"])
        assert decoded_token["user_id"] == str(user.id)


class TestPasswordReset:
    """Tests for password reset flow using real database"""

    def test_reset_password_success(self, auth_service: AuthService):
        """Test successful password reset"""
        # Create user with known password
        original_password = "OriginalPass123!@#"
        user = DataFactory.create_user(password=original_password)

        # Set up reset token with ample expiration time
        reset_token = "valid_reset_token"
        user.reset_token = reset_token
        user.reset_token_expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        user.save()
        user.reload()  # Ensure we have the latest state

        # Reset password
        new_password = "NewPassword123!@#"
        auth_service.reset_password(reset_token, new_password)

        # Verify user state after reset
        user.reload()
        assert user.reset_token is None
        assert user.reset_token_expiration is None

        # Verify old password no longer works
        with pytest.raises(LoginError):
            auth_service.login(
                LoginData(email_or_username=user.email, password=original_password)
            )

        # Verify can login with new password
        logged_in_user, tokens = auth_service.login(
            LoginData(email_or_username=user.email, password=new_password)
        )
        assert logged_in_user is not None
        assert tokens["access_token"] is not None

    def test_reset_password_expired_token(self, auth_service: AuthService):
        """Test password reset fails with expired token"""
        user = DataFactory.create_user()
        reset_token = "expired_token"
        user.reset_token = reset_token
        user.reset_token_expiration = datetime.now(timezone.utc) - timedelta(minutes=1)
        user.save()

        with pytest.raises(AuthError):
            auth_service.reset_password(reset_token, "NewPassword123!@#")

    def test_reset_password_invalid_token(self, auth_service: AuthService):
        """Test password reset fails with invalid token"""
        with pytest.raises(AuthError, match="Invalid or expired token"):
            auth_service.reset_password("invalid_token", "NewPassword123!@#")


class TestTokenRefresh:
    """Tests for token refresh flow using real database"""

    def test_refresh_token_success(self, auth_service: AuthService):
        """Test successful token refresh"""
        user = DataFactory.create_user()
        user_data = {
            "id": str(user.id),
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
        }
        refresh_token = auth_service._generate_token(
            user_data, expires_in=timedelta(days=30)
        )

        user_data, new_access_token = auth_service.refresh_token(refresh_token)

        assert new_access_token is not None
        assert user_data["id"] == str(user.id)
        assert user_data["username"] == user.username

    def test_refresh_token_blacklisted(self, auth_service: AuthService):
        """Test refresh fails with blacklisted token"""
        user = DataFactory.create_user()
        user_data = {"id": str(user.id), "user_id": str(user.id)}
        refresh_token = auth_service._generate_token(
            user_data, expires_in=timedelta(days=30)
        )

        # Blacklist the token
        user.blacklist_token(refresh_token)
        user.save()

        with pytest.raises(TokenError, match="Refresh token has been invalidated"):
            auth_service.refresh_token(refresh_token)

    def test_refresh_token_expired(self, auth_service: AuthService):
        """Test refresh fails with expired token"""
        user = DataFactory.create_user()
        user_data = {
            "id": str(user.id),
            "user_id": str(user.id),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(user_data, "test_secret", algorithm="HS256")

        with pytest.raises(TokenError):
            auth_service.refresh_token(expired_token)

    def test_refresh_token_invalid(self, auth_service: AuthService):
        """Test refresh fails with invalid token"""
        with pytest.raises(TokenError, match="Invalid refresh token"):
            auth_service.refresh_token("invalid_token")


class TestLogout:
    """Tests for logout functionality using real database"""

    def test_logout_success(self, auth_service: AuthService):
        """Test successful logout"""
        user = DataFactory.create_user()
        token = auth_service._generate_token(
            {"id": str(user.id), "user_id": str(user.id)}
        )

        auth_service.logout(token)

        user.reload()
        assert token in user.blacklisted_tokens

    def test_logout_invalid_token(self, auth_service: AuthService):
        """Test logout with invalid token doesn't raise error"""
        auth_service.logout("invalid_token")  # Should not raise

    def test_logout_nonexistent_user(self, auth_service: AuthService):
        """Test logout with token for nonexistent user"""
        user = DataFactory.create_user()
        token = auth_service._generate_token(
            {"id": str(user.id), "user_id": str(user.id)}
        )

        # Delete the user
        user.delete()

        auth_service.logout(token)  # Should not raise


class TestIdempotentOperation:
    """Tests for idempotent operation decorator"""

    def test_operation_succeeds_first_try(self, auth_service: AuthService):
        """Test operation succeeds on first attempt"""
        # Create user with known password
        password = "Test123!@#"
        user = DataFactory.create_user(password=password)

        # Attempt login
        login_data = LoginData(email_or_username=user.email, password=password)
        logged_in_user, tokens = auth_service.login(login_data)

        assert logged_in_user is not None
        assert tokens is not None
        assert tokens["access_token"] is not None
        assert tokens["refresh_token"] is not None

    def test_operation_succeeds_after_retry(
        self, auth_service: AuthService, monkeypatch
    ):
        """Test operation succeeds after initial failure"""
        # Create user with known password
        password = "Test123!@#"
        user = DataFactory.create_user(password=password)

        # Set up counter for mock behavior
        fail_count = [0]
        from werkzeug.security import check_password_hash

        original_check_password_hash = check_password_hash

        def mock_check_password_hash(hashed_password, password):
            if fail_count[0] == 0:
                fail_count[0] += 1
                raise Exception("Temporary failure")
            return original_check_password_hash(hashed_password, password)

        # Patch the password check function
        monkeypatch.setattr(
            "werkzeug.security.check_password_hash", mock_check_password_hash
        )

        # Attempt login
        login_data = LoginData(email_or_username=user.email, password=password)
        logged_in_user, tokens = auth_service.login(login_data)

        assert logged_in_user is not None
        assert tokens is not None
        assert fail_count[0] == 1  # Verify we hit the failure case

    def test_operation_fails_after_max_retries(
        self, auth_service: AuthService, monkeypatch
    ):
        """Test operation fails after maximum retries"""
        # Create user with known password
        password = "Test123!@#"
        user = DataFactory.create_user(password=password)

        # Mock check_password_hash to always fail
        def mock_check_password_hash(hashed_password, password):
            raise Exception("Persistent failure")

        monkeypatch.setattr(
            "werkzeug.security.check_password_hash", mock_check_password_hash
        )

        # Attempt login
        login_data = LoginData(email_or_username=user.email, password=password)
        with pytest.raises(Exception, match="Persistent failure"):
            auth_service.login(login_data)
