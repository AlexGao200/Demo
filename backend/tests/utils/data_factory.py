import uuid
from typing import Optional
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

from services.auth_service import RegistrationData, LoginData
from models.user import User
from models.organization import Organization
from models.user_organization import UserOrganization
from models.invitation import Invitation
from services.document_ingestion_service import slugify
from config.test import TestConfig


class DataFactory:
    """Factory for generating unique test data"""

    _test_config = TestConfig()

    @staticmethod
    def get_unique_email(prefix: str = "test") -> str:
        """Generate a unique email address"""
        return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"

    @staticmethod
    def unique_username(prefix: str = "user") -> str:
        """Generate a unique username"""
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def unique_org_identifier() -> str:
        """Generate a unique identifier for organization-related fields"""
        return uuid.uuid4().hex[:8]

    @classmethod
    def create_user(
        cls,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        first_name: str = "Test",
        last_name: str = "User",
        is_verified: bool = True,
        is_superadmin: bool = False,
        subscription_status: str = "none",
        cycle_token_limit: Optional[int] = None,
        save: bool = True,
        last_login: Optional[datetime] = None,
    ) -> User:
        """Create a user with unique email/username if not provided"""
        # Use test config password if none provided
        if password is None:
            password = cls._test_config.TEST_USER_PASSWORD

        user = User(
            email=email or cls.get_unique_email(),
            username=username or cls.unique_username(),
            password=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            is_verified=is_verified,
            is_superadmin=is_superadmin,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            subscription_status=subscription_status,
            cycle_token_limit=cycle_token_limit,
            blacklisted_tokens=[],
            is_deleted=False,
            last_login=last_login or datetime.now(timezone.utc),
        )
        if save:
            user.save()
        return user

    @classmethod
    def create_organization(
        cls,
        name: Optional[str] = None,
        slug_name: Optional[str] = None,
        password: Optional[str] = None,
        email_suffix: Optional[str] = None,
        organization_contract: str = "active",
        has_public_documents: bool = False,
        save: bool = True,
    ) -> Organization:
        """Create an organization with unique name/slug/index if not provided"""
        unique_id = cls.unique_org_identifier()

        # Generate unique name if not provided
        org_name = name or f"Test Organization {unique_id}"

        # Generate unique slug if not provided, or ensure provided slug is unique
        if slug_name:
            # Append unique identifier to provided slug to ensure uniqueness
            org_slug = f"{slugify(slug_name)}_{unique_id}"
        else:
            org_slug = f"{slugify(org_name)}_{unique_id}"

        # Generate unique index name
        index_name = f"test_index_{unique_id}"

        # Use test config password if none provided
        if password is None:
            password = cls._test_config.TEST_USER_PASSWORD

        org = Organization(
            name=org_name,
            slug_name=org_slug,
            index_name=index_name,
            password=generate_password_hash(password),
            email_suffix=email_suffix,
            organization_contract=organization_contract,
            has_public_documents=has_public_documents,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        if save:
            org.save()
        return org

    @staticmethod
    def create_user_organization(
        user: User,
        organization: Organization,
        role: str = "member",
        is_paid: bool = False,
        is_active: bool = True,
        save: bool = True,
    ) -> UserOrganization:
        """Create a user-organization relationship"""
        user_org = UserOrganization(
            user=user,
            organization=organization,
            role=role,
            is_paid=is_paid,
            is_active=is_active,
            joined_at=datetime.now(timezone.utc),
            index_name=organization.index_name or "",
        )
        if save:
            user_org.save()
        return user_org

    @staticmethod
    def create_invitation(
        email: str,
        organization: Organization,
        token: str,
        user: Optional[User] = None,
        accepted: bool = False,
        save: bool = True,
    ) -> Invitation:
        """Create an invitation for a user to join an organization"""
        now = datetime.now(timezone.utc)
        invitation = Invitation(
            organization=organization,
            token=token,
            sent_at=now,
            created_at=now,
            accepted=accepted,
            user=user,
            email=email,
        )
        if save:
            invitation.save()
        return invitation

    @classmethod
    def registration_data(
        cls,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        first_name: str = "Test",
        last_name: str = "User",
        invitation_token: Optional[str] = None,
        organization_registration_code: Optional[str] = None,
    ) -> RegistrationData:
        """Generate unique registration data"""
        # Use test config password if none provided
        if password is None:
            password = cls._test_config.TEST_USER_PASSWORD

        return RegistrationData(
            email=email or cls.get_unique_email(),
            username=username or cls.unique_username(),
            password=password,
            first_name=first_name,
            last_name=last_name,
            invitation_token=invitation_token,
            organization_registration_code=organization_registration_code,
        )

    @classmethod
    def login_data(
        cls,
        email_or_username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> LoginData:
        """Generate login data"""
        # Use test config password if none provided
        if password is None:
            password = cls._test_config.TEST_USER_PASSWORD

        return LoginData(
            email_or_username=email_or_username or cls.get_unique_email(),
            password=password,
        )
