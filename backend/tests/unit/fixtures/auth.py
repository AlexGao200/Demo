from datetime import datetime, timezone, timedelta
import pytest
from auth.utils import generate_token
from models.user import User


@pytest.fixture
def valid_user_data():
    """Valid user data for registration tests"""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewUser123!@#",
        "first_name": "New",
        "last_name": "User",
    }


@pytest.fixture
def regular_auth_headers(test_user, minimal_app):
    """Generate valid auth headers using test user."""
    with minimal_app.app_context():
        print("\nGenerating auth headers:")
        print(f"User ID: {test_user.id}")

        # Verify user exists
        db_user = User.objects(id=test_user.id).first()
        print(f"User exists in DB: {db_user is not None}")
        if not db_user:
            raise Exception("User not found when generating auth headers")

        user_data = {
            "id": str(test_user.id),
            "username": test_user.username,
            "email": test_user.email,
            "first_name": test_user.first_name,
            "last_name": test_user.last_name,
            "personal_index_name": getattr(test_user, "personal_index_name", ""),
            "is_superadmin": getattr(test_user, "is_superadmin", False),
            "subscription_status": "active",
            "cycle_token_limit": 1000,
            "last_login": datetime.now(timezone.utc),
            "organization_indices": getattr(test_user, "organization_indices", []),
        }

        # Generate JWT token
        token = generate_token(
            user_data=user_data,
            secret_key=minimal_app.config["SECRET_KEY"],
            expires_in=timedelta(days=1),
        )

        print("Auth token generated successfully")
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def guest_auth_headers(test_guest_user):
    """Create authentication headers for guest user tests."""
    guest_user, session_id = test_guest_user
    token = f"guest_{session_id}" if not session_id.startswith("guest_") else session_id
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(regular_auth_headers):
    """Alias for regular_auth_headers for backward compatibility."""
    return regular_auth_headers


def create_test_auth_token(
    user_data: dict, secret_key: str, expires_in: timedelta = timedelta(days=1)
) -> str:
    """
    Utility function to create test auth tokens.

    Args:
        user_data (dict): User data to encode in token
        secret_key (str): Secret key for token signing
        expires_in (timedelta): Token expiration time

    Returns:
        str: JWT token
    """
    return generate_token(
        user_data=user_data, secret_key=secret_key, expires_in=expires_in
    )
