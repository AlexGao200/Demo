import pytest
from unittest.mock import MagicMock
import uuid
from werkzeug.security import generate_password_hash
from typing import Optional

from models.organization import Organization
from models.user_organization import UserOrganization
from services.organization_service import OrganizationService
from services.document_ingestion_service import slugify


@pytest.fixture
def organization_service(mock_index_service):
    """Create organization service with mock index service"""
    service = OrganizationService(index_service=mock_index_service)
    return service


@pytest.fixture
def test_organization(test_user):
    """
    Create a test organization with the test user as admin.

    Args:
        test_user: Test user fixture

    Returns:
        Organization: Test organization instance
    """
    # Generate a unique name to support parallel testing
    org_name = f"Test Organization {uuid.uuid4().hex[:8]}"

    organization = Organization(
        name=org_name,
        slug_name=slugify(org_name),
        password=generate_password_hash("test_password"),
        index_name=f"test_index_{uuid.uuid4().hex[:8]}",  # Unique index name
        email_suffix="test.com",
    ).save()

    # Add test user as admin
    UserOrganization(
        user=test_user,
        organization=organization,
        role="admin",
        index_name=organization.index_name,
        is_active=True,
    ).save()

    return organization


def create_test_organization(
    name: Optional[str] = None,
    email_suffix: str = "test.com",
    password: str = "test_password",
) -> Organization:
    """
    Helper function to create test organizations.

    Args:
        name: Optional organization name (generated if not provided)
        email_suffix: Email suffix for organization
        password: Organization password

    Returns:
        Organization: Created organization instance
    """
    if name is None:
        name = f"Test Organization {uuid.uuid4().hex[:8]}"

    return Organization(
        name=name,
        slug_name=slugify(name),
        password=generate_password_hash(password),
        index_name=f"test_index_{uuid.uuid4().hex[:8]}",
        email_suffix=email_suffix,
    ).save()


@pytest.fixture
def mock_organization_service():
    """
    Create a fully mocked organization service for testing.

    Returns:
        MagicMock: Mocked organization service
    """
    mock = MagicMock(spec=OrganizationService)

    # Configure standard responses
    mock.create_organization.return_value = create_test_organization()
    mock.get_organization.return_value = create_test_organization()
    mock.update_organization.return_value = True
    mock.delete_organization.return_value = True

    # Mock user management methods
    mock.add_user_to_organization.return_value = True
    mock.remove_user_from_organization.return_value = True
    mock.update_user_role.return_value = True

    return mock


@pytest.fixture
def test_organization_membership(test_user, test_organization):
    """
    Create a test organization membership.

    Args:
        test_user: Test user fixture
        test_organization: Test organization fixture

    Returns:
        UserOrganization: Test membership instance
    """
    membership = UserOrganization(
        user=test_user,
        organization=test_organization,
        role="member",
        is_active=True,
        index_name=test_organization.index_name,
    ).save()

    return membership


class OrganizationTestError(Exception):
    """Base exception for organization test errors."""

    pass


class OrganizationCreationError(OrganizationTestError):
    """Raised when organization creation fails in tests."""

    pass


class OrganizationMembershipError(OrganizationTestError):
    """Raised when organization membership operations fail in tests."""

    pass


# Export all needed items
__all__ = [
    "organization_service",
    "test_organization",
    "create_test_organization",
    "mock_organization_service",
    "test_organization_membership",
    "OrganizationTestError",
    "OrganizationCreationError",
    "OrganizationMembershipError",
]
