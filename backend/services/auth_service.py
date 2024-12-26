from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from utils.error_handlers import log_error
from werkzeug.security import generate_password_hash, check_password_hash
from mongoengine import get_db
from loguru import logger
from prometheus_client import Counter, Histogram
import jwt
import re
import uuid
import functools
import time
import random
import string
from flask_mail import Message as MailMessage
from flask import current_app

from models.user import User
from models.registration_session import RegistrationSession
from models.invitation import Invitation, RegistrationCode
from services.email_service import EmailService
from services.user_service import UserService

# Metrics
REGISTRATION_ATTEMPTS = Counter(
    "user_registration_attempts", "Number of user registration attempts"
)
REGISTRATION_SUCCESSES = Counter(
    "user_registration_successes", "Number of successful user registrations"
)
REGISTRATION_FAILURES = Counter(
    "user_registration_failures", "Number of failed user registrations"
)
REGISTRATION_DURATION = Histogram(
    "user_registration_duration_seconds", "Duration of user registration process"
)
LOGIN_ATTEMPTS = Counter("user_login_attempts", "Number of user login attempts")
LOGIN_SUCCESSES = Counter("user_login_successes", "Number of successful user logins")
LOGIN_FAILURES = Counter("user_login_failures", "Number of failed user logins")


def generate_verification_code():
    return "".join(random.choices(string.hexdigits, k=6))


def idempotent_operation(max_retries=3, retry_delay=1):
    """
    Decorator for making operations idempotent by retrying on failure.
    Particularly useful for database operations that might fail due to race conditions.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt == max_retries - 1:
                        raise last_error
                    time.sleep(retry_delay)
            return None

        return wrapper

    return decorator


@dataclass
class RegistrationData:
    email: str
    username: str
    password: str
    first_name: str
    last_name: str
    invitation_token: Optional[str] = None
    organization_registration_code: Optional[str] = None


@dataclass
class LoginData:
    email_or_username: str
    password: str


class AuthError(Exception):
    """Base exception for authentication errors"""

    pass


class RegistrationError(AuthError):
    """Base exception for registration errors"""

    pass


class EmailVerificationError(RegistrationError):
    """Raised when email verification fails"""

    pass


class UserExistsError(RegistrationError):
    """Raised when attempting to register an existing user"""

    pass


class InvalidInvitationError(RegistrationError):
    """Raised when invitation token is invalid"""

    pass


class LoginError(AuthError):
    """Raised when login fails"""

    pass


class TokenError(AuthError):
    """Raised when token operations fail"""

    pass


class AuthService:
    """
    Service for handling authentication operations.

    This service follows dependency injection principles and manages user authentication,
    registration, and token operations.
    """

    def __init__(
        self,
        email_service: EmailService,
        secret_key: str,
        user_service: UserService,
    ):
        """
        Initialize AuthService with required dependencies.

        Args:
            email_service: Service for sending emails
            secret_key: Secret key for JWT operations
            user_service: Optional UserService instance
        """
        self.email_service = email_service
        self.secret_key = secret_key
        self.user_service = user_service

    def _serialize_datetime(self, dt: Optional[datetime]) -> Optional[int]:
        """Convert datetime to Unix timestamp integer"""
        if dt is None:
            return None
        return int(dt.replace(tzinfo=timezone.utc).timestamp())

    def _prepare_user_data(self, user: User) -> dict:
        """Prepare user data for token generation and API responses"""
        return {
            "id": str(user.id),
            "user_id": str(user.id),
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "organization_indices": (
                self.user_service.get_organization_index_names(user)
                if self.user_service
                else []
            ),
            "personal_index_name": user.personal_index_name,
            "is_superadmin": user.is_superadmin,
            "subscription_status": user.subscription_status,
            "initial_organization": (
                str(user.initial_organization.id) if user.initial_organization else None
            ),
            "cycle_token_limit": user.cycle_token_limit,
            "last_login": self._serialize_datetime(user.last_login),
        }

    def is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def validate_username(self, username: str) -> tuple[bool, str]:
        """
        Validate username format and availability
        Returns: (is_valid, message)
        """
        min_length = 3
        max_length = 20
        pattern = r"^[a-zA-Z0-9_-]+$"

        if len(username) < min_length or len(username) > max_length:
            return (
                False,
                f"Username must be between {min_length} and {max_length} characters long.",
            )

        if not re.match(pattern, username):
            return (
                False,
                "Username can only contain letters, numbers, underscores, and hyphens.",
            )

        if User.objects(username__iexact=username).first():
            return False, "This username is already taken."

        return True, "Username is available."

    def initiate_registration(self, email: str) -> None:
        """
        Initiate the registration process for a new user.

        Args:
            email: The email address to register

        Raises:
            UserExistsError: If email is already registered
            RegistrationError: For other registration-related errors
        """
        try:
            logger.info(f"Starting registration for email: {email}")

            if not self.is_valid_email(email):
                logger.warning(f"Invalid email format: {email}")
                raise RegistrationError("Invalid email format")

            logger.info("Checking for existing user")
            if User.objects(email=email).first():
                logger.warning(f"User already exists with email: {email}")
                raise UserExistsError("Email already registered")

            logger.info("Looking for existing registration session")
            registration_session = RegistrationSession.objects(email=email).first()
            if not registration_session:
                logger.info("Creating new registration session")
                registration_session = RegistrationSession.create_session(email)
            else:
                logger.info("Refreshing existing registration session")
                registration_session.refresh_verification_code()

            logger.info("Sending verification email")
            self.email_service.send_verification_email(email, registration_session)
            logger.info("Verification email sent successfully")

        except UserExistsError as e:
            logger.error(f"User exists error: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Registration failed with error: {str(e)}", exc_info=True)
            REGISTRATION_FAILURES.inc()
            log_error(e, "Registration initiation failed")
            raise RegistrationError(f"Failed to initiate registration: {str(e)}")

    def verify_email_with_code(self, email: str, code: str) -> bool:
        """
        Verify email using provided verification code.

        Args:
            email: The email address being verified
            code: The verification code to check

        Returns:
            bool: True if verification successful

        Raises:
            EmailVerificationError: If verification fails
        """
        try:
            registration_session = RegistrationSession.objects(email=email).first()
            if not registration_session:
                raise EmailVerificationError("Invalid email")
            if registration_session.verify_code(code):
                return True

            raise EmailVerificationError("Invalid verification code")

        except Exception as e:
            REGISTRATION_FAILURES.inc()
            log_error(e, "Email verification failed")
            raise EmailVerificationError(f"Email verification failed: {str(e)}")

    def verify_email_with_token(self, token: str) -> tuple[bool, str]:
        """
        Verify email using verification token from email link.

        Args:
            token: The verification token from the email link

        Returns:
            tuple[bool, str]: (success, email)

        Raises:
            EmailVerificationError: If verification fails
        """
        try:
            registration_session = RegistrationSession.objects(
                verification_token=token
            ).first()
            if not registration_session:
                raise EmailVerificationError("Invalid token")

            if registration_session.verify_token(token):
                return True, registration_session.email

            raise EmailVerificationError("Token verification failed")

        except Exception as e:
            REGISTRATION_FAILURES.inc()
            log_error(e, "Email verification failed")
            raise EmailVerificationError(f"Email verification failed: {str(e)}")

    @REGISTRATION_DURATION.time()
    @idempotent_operation(max_retries=3, retry_delay=1)
    def complete_registration(
        self, data: RegistrationData
    ) -> tuple[User, Optional[str]]:
        """
        Complete user registration after email verification.

        Args:
            data: RegistrationData containing user information

        Returns:
            tuple[User, Optional[str]]: Newly created user and organization name if applicable

        Raises:
            RegistrationError: If registration fails
        """
        REGISTRATION_ATTEMPTS.inc()

        try:
            registration_session = RegistrationSession.objects(email=data.email).first()
            if (
                not registration_session
                or not registration_session.registration_steps.email_verified
            ):
                raise RegistrationError("Email not verified")

            if User.objects(email__iexact=data.email).first():
                raise UserExistsError("Email already registered")
            if User.objects(username__iexact=data.username).first():
                raise UserExistsError("Username already taken")

            associated_organization = None
            org_name_to_show_user = None

            if data.invitation_token:
                invitation = Invitation.objects(
                    token=data.invitation_token, accepted=False
                ).first()
                if not invitation:
                    raise InvalidInvitationError("Invalid organization invitation")
                if invitation.email.lower() != data.email.lower():
                    logger.info(
                        f"Invitation email: {invitation.email}, data email: {data.email}"
                    )
                    raise InvalidInvitationError("Email does not match invitation")
                associated_organization = invitation.organization

            with get_db().client.start_session() as session:
                with session.start_transaction():
                    new_user = User(
                        first_name=data.first_name,
                        last_name=data.last_name,
                        username=data.username,
                        email=data.email,
                        password=generate_password_hash(data.password),
                        is_verified=True,
                    )

                    if data.organization_registration_code:
                        code_object = RegistrationCode.objects.get(
                            uuid=data.organization_registration_code
                        )
                        if not (code_object and code_object.organization):
                            raise InvalidInvitationError(
                                "Invalid organization registration code"
                            )
                        associated_organization = code_object.organization

                    if associated_organization:
                        new_user.initial_organization = associated_organization
                        new_user.save()
                        self.user_service.add_to_organization(
                            new_user, associated_organization, "member"
                        )
                        associated_organization.save()
                        org_name_to_show_user = associated_organization.name
                    else:
                        new_user.save()

                    if data.invitation_token:
                        invitation.accepted = True
                        invitation.save()

                    registration_session.delete()

            REGISTRATION_SUCCESSES.inc()
            return new_user, org_name_to_show_user

        except Exception as e:
            REGISTRATION_FAILURES.inc()
            log_error(e, "Registration failed")
            raise RegistrationError(f"Registration failed: {str(e)}")

    @idempotent_operation(max_retries=3, retry_delay=1)
    def login(self, data: LoginData) -> tuple[User, dict[str, Any]]:
        """
        Authenticate user and generate tokens
        Returns: (user, tokens)
        """
        LOGIN_ATTEMPTS.inc()
        try:
            user = (
                User.objects(email=data.email_or_username).first()
                or User.objects(username=data.email_or_username).first()
            )

            if not user or not check_password_hash(user.password, data.password):
                LOGIN_FAILURES.inc()
                raise LoginError(f"Invalid login credentials: {user}")

            if not user.is_verified:
                registration_session = RegistrationSession.objects(
                    email=user.email
                ).first()
                if (
                    registration_session
                    and registration_session.registration_steps.email_verified
                ):
                    user.is_verified = True
                    user.save()
                else:
                    raise LoginError("Email address not verified")

            # Update last_login as datetime
            user.last_login = datetime.now(timezone.utc)
            user.save()

            # Prepare user data with serialized datetime
            user_data = self._prepare_user_data(user)

            tokens = {
                "access_token": self._generate_token(user_data),
                "refresh_token": self._generate_token(
                    user_data, expires_in=timedelta(days=30)
                ),
            }

            LOGIN_SUCCESSES.inc()
            return user, tokens

        except Exception as e:
            LOGIN_FAILURES.inc()
            log_error(e, "Login failed")
            raise LoginError(f"Login failed: {str(e)}")

    def refresh_token(self, refresh_token: str) -> tuple[dict[str, Any], str]:
        """
        Refresh access token using refresh token
        Returns: (user_data, new_access_token)
        """
        try:
            decoded_token = jwt.decode(
                refresh_token, self.secret_key, algorithms=["HS256"]
            )
            user_id = decoded_token.get("user_id")

            if not user_id:
                raise TokenError("Invalid refresh token - user_id missing")

            user = User.objects(id=user_id).first()
            if not user:
                raise TokenError("User not found")

            if self.user_service.is_token_blacklisted(user, refresh_token):
                raise TokenError("Refresh token has been invalidated")

            user_data = self._prepare_user_data(user)
            new_access_token = self._generate_token(user_data)
            return user_data, new_access_token

        except jwt.ExpiredSignatureError:
            raise TokenError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise TokenError("Invalid refresh token")
        except Exception as e:
            log_error(e, "Token refresh failed")
            raise TokenError(f"Token refresh failed: {str(e)}")

    def initiate_password_reset(
        self, email: str, frontend_base_url: str
    ) -> Optional[str]:
        """
        Initiate password reset process
        Returns: reset_token (only in debug mode)
        """
        try:
            user = User.objects(email=email).first()
            if not user:
                logger.error("User in password reset must not be none.")
                return None

            reset_token = str(uuid.uuid4())
            user.reset_token = reset_token
            user.reset_token_expiration = datetime.now(timezone.utc) + timedelta(
                hours=1
            )
            user.save()

            reset_link = f"{frontend_base_url}/reset-password/{reset_token}"
            html_content = f'<p>Please click the link to reset your password: <a href="{reset_link}">{reset_link}</a></p>'

            msg = MailMessage(
                "Password Reset Request", recipients=[user.email], html=html_content
            )
            self.email_service.send(msg)

            return reset_token if current_app.config["TESTING"] else None

        except Exception as e:
            log_error(e, "Password reset initiation failed")
            raise AuthError(f"Password reset initiation failed: {str(e)}")

    @idempotent_operation(max_retries=3, retry_delay=1)
    def reset_password(self, token: str, new_password: str) -> None:
        """Reset user password using reset token"""
        try:
            user = User.objects(reset_token=token).first()
            if not user:
                raise AuthError("Invalid or expired token")

            if user.reset_token_expiration.replace(tzinfo=timezone.utc) < datetime.now(
                timezone.utc
            ):
                raise AuthError("Reset token has expired")

            user.password = generate_password_hash(new_password)
            user.reset_token = None
            user.reset_token_expiration = None
            user.save()

        except Exception as e:
            log_error(e, "Password reset failed")
            raise AuthError(f"Password reset failed: {str(e)}")

    def logout(self, token: str) -> None:
        """Logout user by blacklisting their token"""
        try:
            decoded_token = jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            logger.warning("Invalid token provided for logout")
            return

        user_id = decoded_token.get("user_id")
        if not user_id:
            logger.warning("Token missing user_id during logout")
            return

        user = User.objects(id=user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found during logout")
            return

        self.user_service.blacklist_token(user, token)

        if not self.user_service.is_token_blacklisted(user, token):
            raise AuthError("Failed to blacklist token")

    def _generate_token(
        self, user_data: dict[str, Any], expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate JWT token with user data"""
        try:
            expiration_time = datetime.now(timezone.utc) + expires_in
            payload = {
                **user_data,
                "exp": int(expiration_time.timestamp()),
            }
            return jwt.encode(payload, self.secret_key, algorithm="HS256")
        except Exception as e:
            log_error(e, "Token generation failed")
            raise TokenError(f"Token generation failed: {str(e)}")

    def create_access_token(
        self, user: User, expires_in: Optional[timedelta] = None
    ) -> str:
        """
        Create an access token for a user.

        This method provides a stable interface for generating access tokens,
        particularly useful for testing scenarios while maintaining proper encapsulation.

        Args:
            user: The user to generate token for
            expires_in: Optional custom expiration time. Defaults to 1 hour if not specified.

        Returns:
            str: The generated access token

        Raises:
            TokenError: If token generation fails
        """
        try:
            user_data = self._prepare_user_data(user)
            return self._generate_token(user_data, expires_in or timedelta(hours=1))
        except Exception as e:
            log_error(e, "Access token creation failed")
            raise TokenError(f"Access token creation failed: {str(e)}")

    def verify_token(self, token: str) -> bool:
        """
        Verify if a token is valid and not blacklisted.

        Args:
            token: The JWT token to verify

        Returns:
            bool: True if token is valid and not blacklisted

        Raises:
            TokenError: If token verification fails
        """
        try:
            decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id = decoded.get("user_id")

            if not user_id:
                return False

            user = User.objects(id=user_id).first()
            if not user:
                return False

            if self.user_service.is_token_blacklisted(user, token):
                return False

            return True

        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
        except Exception as e:
            log_error(e, "Token verification failed")
            raise TokenError(f"Token verification failed: {str(e)}")
