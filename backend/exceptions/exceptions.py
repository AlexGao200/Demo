# Custom exceptions


class SessionError(Exception):
    """Base exception for session-related errors"""

    pass


class SessionExpiredError(SessionError):
    """Raised when a session has expired"""

    pass


class MessageLimitError(SessionError):
    """Raised when message limit is reached"""

    pass
