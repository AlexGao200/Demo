import pytest
import uuid
from unittest.mock import Mock
from datetime import datetime, timezone
from typing import Dict, Optional

from models.user import User
from models.registration_session import RegistrationSession
from werkzeug.security import generate_password_hash


@pytest.fixture
def user_service():
    """Mock user service for auth testing"""
    mock = Mock()

    # Setup common methods used by AuthService
    mock.get_user_by_id.return_value = None
    mock.get_user_by_username.return_value = None
    mock.blacklist_token.return_value = None
    mock.is_token_blacklisted.return_value = False
    mock.generate_verification_token.return_value = None

    return mock


@pytest.fixture
def test_user_data() -> Dict[str, str]:
    """
    Generate unique test user data for each test.
    Creates unique identifiers to prevent test collisions.

    Returns:
        dict: Test user data with unique email and username
    """
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"test_{unique_id}@example.com",
        "username": f"testuser_{unique_id}",
        "password": "Test123!@#",
        "first_name": "Test",
        "last_name": "User",
        "is_verified": True,
    }


@pytest.fixture
def test_user(test_user_data, minimal_app):
    """Create a test user in the database with unique credentials."""
    with minimal_app.app_context():
        # Clean up any existing test users first
        User.objects(email__startswith="test_").delete()

        user = User(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"],
            first_name=test_user_data["first_name"],
            last_name=test_user_data["last_name"],
            is_verified=test_user_data["is_verified"],
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
            subscription_status="active",
            cycle_token_limit=1000,
            is_guest=False,
            personal_index_name=f"user_{uuid.uuid4().hex[:8]}",
        )
        user.save()

        # Force a database query to verify persistence
        persisted_user = User.objects(id=user.id).first()
        print("\nVerifying user persistence:")
        print(f"User ID: {user.id}")
        print(f"Found in DB: {persisted_user is not None}")
        if not persisted_user:
            raise Exception("User was not persisted to database")

        # Store user data for potential recreation
        user._test_data = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "password": user.password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "subscription_status": user.subscription_status,
            "cycle_token_limit": user.cycle_token_limit,
            "is_guest": user.is_guest,
            "personal_index_name": user.personal_index_name,
        }

        yield user

        # Clean up after the test
        User.objects(id=user.id).delete()


@pytest.fixture(autouse=True)
def ensure_test_user_exists():
    """Ensure test user exists throughout test execution"""
    yield
    # After each test, check if we need to restore any test users
    for user in User._get_collection().find({"email": {"$regex": "^test_"}}):
        if not User.objects(id=user["_id"]).first():
            User(**user).save()


@pytest.fixture
def valid_user_data() -> Dict[str, str]:
    """
    Valid user data for registration tests.
    Provides static data for consistent registration testing.

    Returns:
        dict: Valid registration data
    """
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewUser123!@#",
        "first_name": "New",
        "last_name": "User",
    }


def create_test_user(
    email: Optional[str] = None,
    username: Optional[str] = None,
    password: str = "Test123!@#",
    is_verified: bool = True,
    is_guest: bool = False,
    **kwargs,
) -> User:
    """
    Helper function to create test users with custom attributes.

    Args:
        email: Optional email (generated if not provided)
        username: Optional username (generated if not provided)
        password: Password for the user
        is_verified: Whether the user is verified
        is_guest: Whether this is a guest user
        **kwargs: Additional user attributes

    Returns:
        User: Created user instance
    """
    unique_id = str(uuid.uuid4())[:8]

    user_data = {
        "email": email or f"test_{unique_id}@example.com",
        "username": username or f"testuser_{unique_id}",
        "password": generate_password_hash(password),
        "first_name": kwargs.get("first_name", "Test"),
        "last_name": kwargs.get("last_name", "User"),
        "is_verified": is_verified,
        "is_guest": is_guest,
        "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
        "last_login": kwargs.get("last_login", datetime.now(timezone.utc)),
        "subscription_status": kwargs.get("subscription_status", "active"),
        "cycle_token_limit": kwargs.get("cycle_token_limit", 1000),
        "personal_index_name": kwargs.get(
            "personal_index_name", f"user_{uuid.uuid4().hex[:8]}"
        ),
    }

    user = User(**user_data)
    user.save()

    return user


@pytest.fixture
def test_guest_user():
    """
    Create a test guest user.

    Returns:
        User: Created guest user instance
    """
    user = create_test_user(
        is_guest=True, subscription_status="guest", cycle_token_limit=100
    )
    yield user
    user.delete()


@pytest.fixture
def test_registration_session(test_user_data):
    """
    Create a test registration session.

    Args:
        test_user_data: Fixture providing user data

    Returns:
        RegistrationSession: Created registration session
    """
    session = RegistrationSession(
        email=test_user_data["email"],
        verification_token="test_token",
        created_at=datetime.now(timezone.utc),
    ).save()

    yield session

    session.delete()


class UserTestError(Exception):
    """Base exception for user test errors."""

    pass


class UserCreationError(UserTestError):
    """Raised when user creation fails in tests."""

    pass


class UserVerificationError(UserTestError):
    """Raised when user verification fails in tests."""

    pass


# Export all needed items
__all__ = [
    "test_user_data",
    "test_user",
    "valid_user_data",
    "create_test_user",
    "test_guest_user",
    "test_registration_session",
    "UserTestError",
    "UserCreationError",
    "UserVerificationError",
]
