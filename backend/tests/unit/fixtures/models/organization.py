import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from werkzeug.security import generate_password_hash

from models.organization import Organization
from models.user_organization import UserOrganization
from models.index_registry import IndexRegistry, FilterDimension
from models.invitation import Invitation, RegistrationCode
from services.document_ingestion_service import slugify


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
        index_name=f"test_index_{uuid.uuid4().hex[:8]}",
        email_suffix="test.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).save()

    # Add test user as admin
    UserOrganization(
        user=test_user,
        organization=organization,
        role="admin",
        index_name=organization.index_name,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    ).save()

    yield organization

    # Cleanup organization and related records
    UserOrganization.objects(organization=organization).delete()
    IndexRegistry.objects(entity_id=str(organization.id)).delete()
    organization.delete()


@pytest.fixture
def test_index_registry(test_organization):
    """
    Create a test index registry that matches the test organization.

    Args:
        test_organization: Test organization fixture

    Returns:
        IndexRegistry: Created index registry
    """
    index = IndexRegistry(
        index_name=test_organization.index_name,
        filter_dimensions=[],
        index_display_name=test_organization.name,
        entity_type="organization",
        entity_id=str(test_organization.id),
    ).save()

    yield index

    index.delete()


@pytest.fixture
def test_filter_dimension():
    """
    Create a test filter dimension.

    Returns:
        FilterDimension: Created filter dimension
    """
    dimension = FilterDimension(
        name="test_dimension",
        values=["value1", "value2", "value3"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).save()

    yield dimension

    dimension.delete()


@pytest.fixture
def test_index_with_filters(test_filter_dimension, test_organization):
    """
    Create a test index registry with filter dimensions.

    Args:
        test_filter_dimension: Test filter dimension fixture
        test_organization: Test organization fixture

    Returns:
        IndexRegistry: Created index registry with filters
    """
    index = IndexRegistry(
        index_name=test_organization.index_name,
        filter_dimensions=[test_filter_dimension],
        index_display_name=test_organization.name,
        entity_type="organization",
        entity_id=str(test_organization.id),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).save()

    yield index

    index.delete()


@pytest.fixture
def test_invitation(test_organization, test_user):
    """
    Create a test invitation.

    Args:
        test_organization: Test organization fixture
        test_user: Test user fixture

    Returns:
        Invitation: Created invitation
    """
    invitation = Invitation(
        organization=test_organization,
        inviter=test_user,
        email="invited@example.com",
        role="member",
        token=str(uuid.uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
    ).save()

    yield invitation

    invitation.delete()


@pytest.fixture
def test_registration_code(test_organization):
    """
    Create a test registration code.

    Args:
        test_organization: Test organization fixture

    Returns:
        RegistrationCode: Created registration code
    """
    code = RegistrationCode(
        organization=test_organization,
        code=str(uuid.uuid4())[:8].upper(),
        role="member",
        max_uses=10,
        uses=0,
        created_at=datetime.now(timezone.utc),
    ).save()

    yield code

    code.delete()


def create_test_organization(
    name: Optional[str] = None,
    email_suffix: str = "test.com",
    password: str = "test_password",
    **kwargs,
) -> Organization:
    """
    Helper function to create test organizations.

    Args:
        name: Optional organization name (generated if not provided)
        email_suffix: Email suffix for organization
        password: Organization password
        **kwargs: Additional organization attributes

    Returns:
        Organization: Created organization instance
    """
    if name is None:
        name = f"Test Organization {uuid.uuid4().hex[:8]}"

    org_data = {
        "name": name,
        "slug_name": slugify(name),
        "password": generate_password_hash(password),
        "index_name": f"test_index_{uuid.uuid4().hex[:8]}",
        "email_suffix": email_suffix,
        "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
        "updated_at": kwargs.get("updated_at", datetime.now(timezone.utc)),
    }

    return Organization(**org_data).save()


def create_user_organization(
    user, organization: Organization, role: str = "member", is_active: bool = True
) -> UserOrganization:
    """
    Helper function to create organization memberships.

    Args:
        user: User to add to organization
        organization: Organization to add user to
        role: User's role in the organization
        is_active: Whether the membership is active

    Returns:
        UserOrganization: Created membership instance
    """
    return UserOrganization(
        user=user,
        organization=organization,
        role=role,
        index_name=organization.index_name,
        is_active=is_active,
        joined_at=datetime.now(timezone.utc),
    ).save()


class OrganizationModelError(Exception):
    """Base exception for organization model test errors."""

    pass


# Export all needed items
__all__ = [
    "test_organization",
    "test_index_registry",
    "test_filter_dimension",
    "test_index_with_filters",
    "test_invitation",
    "test_registration_code",
    "create_test_organization",
    "create_user_organization",
    "OrganizationModelError",
]
