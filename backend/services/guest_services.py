from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict
from uuid import uuid4
from loguru import logger
from models.user import User
from models.chat import Chat
from models.organization import Organization


class GuestSessionManager:
    def __init__(self):
        # Core session management settings
        self.GUEST_SESSION_DURATION = timedelta(hours=6)
        self.MAX_MESSAGES_PER_SESSION = 50
        logger.info(
            f"GuestSessionManager initialized with duration={self.GUEST_SESSION_DURATION}, "
            f"max_messages={self.MAX_MESSAGES_PER_SESSION}"
        )

    def _create_guest_user(self, session_id: str) -> User:
        """Helper method to create a guest user with a specific session ID"""
        try:
            expires_at = datetime.now(timezone.utc) + self.GUEST_SESSION_DURATION
            logger.debug(
                f"Creating guest user - Session ID: {session_id}, Expires: {expires_at}"
            )

            guest_user = User(
                first_name="Guest",
                last_name="User",
                username=session_id,
                email=f"{session_id}@guest.temporary",
                password=uuid4().hex,  # Random password
                is_guest=True,
                is_verified=True,
                session_id=session_id,
                created_at=datetime.now(timezone.utc),
                session_expires_at=expires_at,
                subscription_status="guest",
                cycle_token_limit=self.MAX_MESSAGES_PER_SESSION,
                current_cycle_message_count=0,
            ).save()

            logger.info(
                f"Guest user created successfully - "
                f"Session: {session_id}, "
                f"Expires: {expires_at}, "
                f"Message Limit: {self.MAX_MESSAGES_PER_SESSION}"
            )
            return guest_user
        except Exception as e:
            logger.error(
                f"Failed to create guest user - "
                f"Session: {session_id}, "
                f"Error: {str(e)}",
                exc_info=True,
            )
            raise

    def get_or_create_guest_session(
        self, session_id: Optional[str] = None
    ) -> Tuple[User, str]:
        """Get existing guest session or create new one"""
        logger.debug(
            f"get_or_create_guest_session called with session_id: {session_id}"
        )

        if session_id:
            normalized_session_id = (
                session_id if session_id.startswith("guest_") else f"guest_{session_id}"
            )
            logger.debug(f"Normalized session ID: {normalized_session_id}")

            guest_user = User.objects(
                session_id=normalized_session_id,
                is_guest=True,
                session_expires_at__gt=datetime.now(timezone.utc),
            ).first()

            if guest_user:
                logger.info(f"Found existing session: {normalized_session_id}")
                is_valid = self.is_session_valid(guest_user)
                logger.info(
                    f"Session validity check - "
                    f"Session: {normalized_session_id}, "
                    f"Valid: {is_valid}"
                )
                if is_valid:
                    return guest_user, normalized_session_id

            logger.info(
                f"Creating new session with provided ID: {normalized_session_id}"
            )
            try:
                guest_user = self._create_guest_user(normalized_session_id)
                return guest_user, normalized_session_id
            except Exception as e:
                logger.error(
                    f"Failed to create guest session - "
                    f"Session: {normalized_session_id}, "
                    f"Error: {str(e)}"
                )
                raise

        return self.create_guest_session()

    def create_guest_session(self) -> Tuple[User, str]:
        """Create a new guest session with generated ID"""
        session_id = f"guest_{uuid4().hex}"
        logger.info(f"Generating new guest session with ID: {session_id}")
        try:
            guest_user = self._create_guest_user(session_id)
            return guest_user, session_id
        except Exception as e:
            logger.error(
                f"Failed to create new guest session - Error: {str(e)}", exc_info=True
            )
            raise

    def is_session_valid(self, guest_user: User) -> bool:
        """
        Check if a guest session is still valid with detailed logging
        """
        logger.debug(f"Checking session validity for user: {guest_user.session_id}")

        # Log initial state
        logger.debug(
            f"Session state - "
            f"Is Guest: {guest_user.is_guest}, "
            f"Message Count: {guest_user.current_cycle_message_count}, "
            f"Expires At: {guest_user.session_expires_at}"
        )

        if not guest_user.is_guest:
            logger.warning(
                f"Invalid guest status - "
                f"Session: {guest_user.session_id}, "
                f"Is Guest: {guest_user.is_guest}"
            )
            return False

        current_time = datetime.now(timezone.utc)
        expires_at = guest_user.session_expires_at

        # Ensure session_expires_at is timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            logger.debug(
                f"Made expiration timezone-aware - "
                f"Session: {guest_user.session_id}, "
                f"Expires At: {expires_at}"
            )

        # Check expiration
        if current_time > expires_at:
            logger.info(
                f"Session expired - "
                f"Session: {guest_user.session_id}, "
                f"Current Time: {current_time}, "
                f"Expired At: {expires_at}"
            )
            return False

        # Check message limit
        if guest_user.current_cycle_message_count >= self.MAX_MESSAGES_PER_SESSION:
            logger.info(
                f"Message limit reached - "
                f"Session: {guest_user.session_id}, "
                f"Current Count: {guest_user.current_cycle_message_count}, "
                f"Limit: {self.MAX_MESSAGES_PER_SESSION}"
            )
            return False

        # Log successful validation
        logger.info(
            f"Session validated successfully - "
            f"Session: {guest_user.session_id}, "
            f"Expires In: {expires_at - current_time}, "
            f"Messages Remaining: {self.MAX_MESSAGES_PER_SESSION - guest_user.current_cycle_message_count}"
        )
        return True

    def cleanup_expired_sessions(self):
        """Remove expired guest sessions"""
        current_time = datetime.now(timezone.utc)
        logger.info("Starting cleanup of expired guest sessions")

        expired_users = User.objects(is_guest=True, session_expires_at__lt=current_time)
        expired_count = expired_users.count()
        logger.info(f"Found {expired_count} expired sessions to clean up")

        success_count = 0
        error_count = 0

        for user in expired_users:
            try:
                logger.debug(f"Cleaning up session: {user.session_id}")
                chat_count = Chat.objects(user=user).count()
                Chat.objects(user=user).delete()
                user.delete()
                success_count += 1
                logger.info(
                    f"Cleaned up session successfully - "
                    f"Session: {user.session_id}, "
                    f"Chats Removed: {chat_count}"
                )
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to cleanup session - "
                    f"Session: {user.session_id}, "
                    f"Error: {str(e)}",
                    exc_info=True,
                )

        logger.info(
            f"Cleanup completed - "
            f"Total: {expired_count}, "
            f"Successful: {success_count}, "
            f"Failed: {error_count}"
        )


class GuestService:
    # Class-level constants
    GUEST_SESSION_DURATION = timedelta(hours=6)
    MAX_MESSAGES_PER_SESSION = 30

    @staticmethod
    def get_organization_indices_for_guest() -> List[Dict]:
        """Get all organization indices accessible to guest users"""
        logger.debug("Fetching organization indices for guest session")
        indices = []

        try:
            organizations = Organization.objects()
            logger.debug(f"Found {len(organizations)} total organizations")

            for org in organizations:
                if org.index_name:
                    indices.append(
                        {
                            "display_name": org.name,
                            "visibility_options_for_user": ["public"],
                            "name": org.index_name,
                            "role_of_current_user": "viewer",
                        }
                    )

            logger.info(
                f"Retrieved organization indices for guest session - "
                f"Total Organizations: {len(organizations)}, "
                f"Accessible Indices: {len(indices)}"
            )
            return indices

        except Exception as e:
            logger.error(
                f"Failed to fetch organization indices for guest - " f"Error: {str(e)}",
                exc_info=True,
            )
            return []
