import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from models.user import User
from models.chat import Chat
from services.guest_services import GuestSessionManager


@pytest.fixture
def mock_guest_manager():
    """
    Mock guest session manager for testing.
    Implements all functionality from GuestSessionManager.
    """
    mock = MagicMock(spec=GuestSessionManager)

    # Set core session management settings
    mock.GUEST_SESSION_DURATION = timedelta(hours=24)
    mock.MAX_MESSAGES_PER_SESSION = 50

    def create_test_guest_user(session_id: str) -> User:
        """Internal helper to create a guest user matching production behavior"""
        guest_user = User(
            first_name="Guest",
            last_name="User",
            username=session_id,
            email=f"{session_id}@guest.temporary",
            password=uuid4().hex,
            is_guest=True,
            is_verified=True,
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            session_expires_at=datetime.now(timezone.utc) + mock.GUEST_SESSION_DURATION,
            subscription_status="guest",
            cycle_token_limit=mock.MAX_MESSAGES_PER_SESSION,
            current_cycle_message_count=0,
        ).save()
        return guest_user

    def get_or_create_mock(session_id=None):
        """Implements get_or_create_guest_session behavior"""
        if session_id:
            normalized_session_id = (
                session_id if session_id.startswith("guest_") else f"guest_{session_id}"
            )

            # Try to find existing user
            guest_user = User.objects(
                session_id=normalized_session_id,
                is_guest=True,
                session_expires_at__gt=datetime.now(timezone.utc),
            ).first()

            if guest_user and mock.is_session_valid(guest_user):
                return guest_user, normalized_session_id

            # Create new user with provided session ID
            guest_user = create_test_guest_user(normalized_session_id)
            return guest_user, normalized_session_id

        # Create new session with generated ID
        session_id = f"guest_{uuid4().hex}"
        guest_user = create_test_guest_user(session_id)
        return guest_user, session_id

    def is_session_valid_mock(guest_user):
        """Implements is_session_valid behavior"""
        if not guest_user.is_guest:
            return False

        current_time = datetime.now(timezone.utc)
        expires_at = guest_user.session_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if current_time > expires_at:
            return False

        if guest_user.current_cycle_message_count >= mock.MAX_MESSAGES_PER_SESSION:
            return False

        return True

    def cleanup_expired_sessions_mock():
        """Implements cleanup_expired_sessions behavior"""
        current_time = datetime.now(timezone.utc)
        expired_users = User.objects(is_guest=True, session_expires_at__lt=current_time)

        for user in expired_users:
            Chat.objects(user=user).delete()
            user.delete()

    # Configure mock methods
    mock.get_or_create_guest_session.side_effect = get_or_create_mock
    mock.is_session_valid.side_effect = is_session_valid_mock
    mock.cleanup_expired_sessions.side_effect = cleanup_expired_sessions_mock

    yield mock

    # Clean up test data
    User.objects(is_guest=True).delete()
    Chat.objects(user__in=User.objects(is_guest=True)).delete()


@pytest.fixture
def test_guest_user(mock_guest_manager):
    """
    Create a test guest user with valid session.

    Args:
        mock_guest_manager: Mock guest manager fixture

    Returns:
        tuple: (User, session_id) - The guest user and their session ID
    """
    guest_user, session_id = mock_guest_manager.get_or_create_guest_session()
    yield guest_user, session_id

    # Clean up the test user and their chats
    Chat.objects(user=guest_user).delete()
    User.objects(id=guest_user.id).delete()


@pytest.fixture
def test_expired_guest_user(mock_guest_manager):
    """
    Create a test guest user with expired session.

    Args:
        mock_guest_manager: Mock guest manager fixture

    Returns:
        User: The expired guest user
    """
    guest_user, _ = mock_guest_manager.get_or_create_guest_session()
    guest_user.session_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    guest_user.save()

    yield guest_user

    # Clean up
    Chat.objects(user=guest_user).delete()
    User.objects(id=guest_user.id).delete()


@pytest.fixture
def test_maxed_guest_user(mock_guest_manager):
    """
    Create a test guest user who has reached message limit.

    Args:
        mock_guest_manager: Mock guest manager fixture

    Returns:
        User: The guest user at message limit
    """
    guest_user, _ = mock_guest_manager.get_or_create_guest_session()
    guest_user.current_cycle_message_count = mock_guest_manager.MAX_MESSAGES_PER_SESSION
    guest_user.save()

    yield guest_user

    # Clean up
    Chat.objects(user=guest_user).delete()
    User.objects(id=guest_user.id).delete()


# Export all needed items
__all__ = [
    "mock_guest_manager",
    "test_guest_user",
    "test_expired_guest_user",
    "test_maxed_guest_user",
]
