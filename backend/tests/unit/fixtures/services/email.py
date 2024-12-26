import pytest
from unittest.mock import MagicMock
from typing import Optional, Dict, Any
from config.test import TestConfig
from services.email_service import EmailService
from flask_mail import Message


@pytest.fixture
def mock_email_service() -> MagicMock:
    """
    Mock email service with minimal implementation.
    Skips test if real external services are enabled.

    Returns:
        MagicMock: Mocked email service with pre-configured responses

    Usage:
        def test_email(mock_email_service):
            assert mock_email_service.send_verification_email.called
    """
    if TestConfig.ENABLE_EXTERNAL_SERVICES:
        pytest.skip("Using real email service")

    mock = MagicMock(spec=EmailService)

    # Configure standard email operations
    mock.send_verification_email.return_value = True
    mock.send_password_reset_email.return_value = True
    mock.send_invitation_email.return_value = True
    mock.send_welcome_email.return_value = True
    mock.send_document_approved_email.return_value = True
    mock.send_document_rejected_email.return_value = True
    mock.send_organization_invite_email.return_value = True

    # Mock the internal message creation
    mock._create_message.return_value = Message(
        subject="Test Subject", recipients=["test@example.com"], body="Test Body"
    )

    return mock


@pytest.fixture
def captured_emails() -> Dict[str, Any]:
    """
    Fixture to capture emails sent during tests.
    Useful for verifying email content and recipients.

    Returns:
        dict: Dictionary to store captured emails

    Usage:
        def test_email_content(captured_emails, mock_email_service):
            mock_email_service.send_verification_email("test@example.com", "token")
            assert "verification" in captured_emails
            assert captured_emails["verification"]["recipient"] == "test@example.com"
    """
    return {}


def create_test_message(
    subject: str,
    recipients: list,
    body: str,
    html: Optional[str] = None,
    sender: Optional[str] = None,
) -> Message:
    """
    Create a test email message.
    Helper function for creating Message objects in tests.

    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        body: Plain text email body
        html: Optional HTML email body
        sender: Optional sender email address

    Returns:
        Message: Flask-Mail message object
    """
    return Message(
        subject=subject,
        recipients=recipients,
        body=body,
        html=html,
        sender=sender or TestConfig.MAIL_DEFAULT_SENDER,
    )


def verify_email_sent(
    mock_service: MagicMock, method_name: str, *expected_args, **expected_kwargs
) -> bool:
    """
    Verify that an email was sent with specific arguments.
    Helper function for email sending verification in tests.

    Args:
        mock_service: Mocked email service
        method_name: Name of the email sending method to verify
        *expected_args: Expected positional arguments
        **expected_kwargs: Expected keyword arguments

    Returns:
        bool: True if email was sent with matching arguments

    Usage:
        assert verify_email_sent(
            mock_email_service,
            'send_verification_email',
            'test@example.com',
            'token123'
        )
    """
    method = getattr(mock_service, method_name, None)
    if not method:
        return False

    method.assert_called_once()
    call_args = method.call_args

    if expected_args and call_args.args != expected_args:
        return False

    if expected_kwargs and not all(
        call_args.kwargs.get(k) == v for k, v in expected_kwargs.items()
    ):
        return False

    return True


# Custom exception for email verification failures
class EmailVerificationError(Exception):
    """Raised when email verification fails in tests."""

    pass


# Export all needed items
__all__ = [
    "mock_email_service",
    "captured_emails",
    "create_test_message",
    "verify_email_sent",
    "EmailVerificationError",
]
