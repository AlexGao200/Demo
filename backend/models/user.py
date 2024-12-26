# backend/models/user.py

import uuid
import warnings
from datetime import datetime, timedelta, timezone

from mongoengine import (
    DateTimeField,
    Document,
    StringField,
    IntField,
    BooleanField,
    EmailField,
    LazyReferenceField,
    signals,
    ListField,
)


class User(Document):
    """
    User document model for MongoDB.

    Note: Business logic has been moved to UserService. Direct usage of model methods
    is deprecated in favor of UserService methods.
    """

    # Existing fields
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    username = StringField(required=True, unique=True)
    email = EmailField(required=True, unique=True)
    password = StringField(required=True)  # Uses scrypt
    is_verified = BooleanField(default=False)

    # Guest-specific fields
    is_guest = BooleanField(default=False)
    session_id = StringField(required=False)  # For guest session tracking
    session_expires_at = DateTimeField(required=False)  # When guest session expires

    # Existing fields continued...
    verification_token = StringField()
    verification_expiration = DateTimeField()
    reset_token = StringField()
    reset_token_expiration = DateTimeField()
    personal_index_name = StringField()
    initial_organization = LazyReferenceField("Organization", required=False)
    is_superadmin = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))
    last_login = DateTimeField(default=datetime.now(timezone.utc))
    blacklisted_tokens = ListField(StringField(), default=list)

    # Account status
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField()
    deletion_reason = StringField()

    # Subscription related
    total_message_count = IntField(default=0)
    current_cycle_message_count = IntField(default=0)
    subscription_status = StringField(
        choices=[
            "active",
            "inactive",
            "trialing",
            "canceled",
            "past_due",
            "unpaid",
            "none",
            "guest",  # Add guest as a subscription status
        ],
        default="none",
    )
    subscription_paid_by = LazyReferenceField("Organization")
    subscription_start_date = DateTimeField()
    subscription_end_date = DateTimeField()
    cycle_token_limit = IntField()
    stripe_customer_id = StringField()
    stripe_subscription_id = StringField()
    subscription_plan_name = StringField()
    has_failed_payment = BooleanField(default=False)

    meta = {
        "indexes": [
            "username",
            "email",
            "stripe_customer_id",
            "subscription_status",
            "cycle_token_limit",
            "is_deleted",
            "blacklisted_tokens",
            # Add new indexes for guest session management
            "session_id",
            "session_expires_at",
            ("is_guest", "session_expires_at"),  # Compound index for cleanup
        ]
    }

    def blacklist_token(self, token):
        """
        DEPRECATED: Use UserService.blacklist_token() instead.
        """
        warnings.warn(
            "User.blacklist_token() is deprecated. Use UserService.blacklist_token() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if token not in self.blacklisted_tokens:
            self.blacklisted_tokens.append(token)
            self.save()

    def is_token_blacklisted(self, token):
        """
        DEPRECATED: Use UserService.is_token_blacklisted() instead.
        """
        warnings.warn(
            "User.is_token_blacklisted() is deprecated. Use UserService.is_token_blacklisted() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return token in self.blacklisted_tokens

    def soft_delete(self, reason=None):
        """
        DEPRECATED: Use UserService.soft_delete() instead.
        """
        warnings.warn(
            "User.soft_delete() is deprecated. Use UserService.soft_delete() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from services.user_service import UserService
        from services.index_service import IndexService

        # Temporary service instantiation - not ideal, but maintains backward compatibility
        user_service = UserService(IndexService())
        user_service.soft_delete(self, reason)

    def get_role_for_organization(self, organization_id):
        """
        DEPRECATED: Use UserService.get_role_for_organization() instead.
        """
        warnings.warn(
            "User.get_role_for_organization() is deprecated. Use UserService.get_role_for_organization() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization

        membership = UserOrganization.objects(
            user=self.id, organization=organization_id
        ).first()
        return membership.role if membership else None

    def set_role_for_organization(self, organization_id, role):
        """
        DEPRECATED: Use UserService.set_role_for_organization() instead.
        """
        warnings.warn(
            "User.set_role_for_organization() is deprecated. Use UserService.set_role_for_organization() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=self.id, organization=organization_id).update_one(
            set__role=role, upsert=True
        )

    def get_organizations(self):
        """
        DEPRECATED: Use UserService.get_organizations() instead.
        """
        warnings.warn(
            "User.get_organizations() is deprecated. Use UserService.get_organizations() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization

        memberships = UserOrganization.objects(user=self.id)
        return [membership.organization for membership in memberships]

    def get_organization_index_names(self):
        """
        DEPRECATED: Use UserService.get_organization_index_names() instead.
        """
        warnings.warn(
            "User.get_organization_index_names() is deprecated. Use UserService.get_organization_index_names() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization
        from models.organization import Organization

        memberships = UserOrganization.objects(user=self.id)
        org_ids = [membership.organization.id for membership in memberships]
        organizations = Organization.objects(id__in=org_ids)
        return [org.index_name for org in organizations if org.index_name]

    def add_to_organization(self, organization, role):
        """
        DEPRECATED: Use UserService.add_to_organization() instead.
        """
        warnings.warn(
            "User.add_to_organization() is deprecated. Use UserService.add_to_organization() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization

        UserOrganization(
            user=self,
            organization=organization,
            role=role,
            index_name=organization.index_name,
        ).save()

    def remove_from_organization(self, organization):
        """
        DEPRECATED: Use UserService.remove_from_organization() instead.
        """
        warnings.warn(
            "User.remove_from_organization() is deprecated. Use UserService.remove_from_organization() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=self.id, organization=organization.id).delete()

    def generate_verification_token(self):
        """
        DEPRECATED: Use UserService.generate_verification_token() instead.
        """
        warnings.warn(
            "User.generate_verification_token() is deprecated. Use UserService.generate_verification_token() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.verification_token = str(uuid.uuid4())
        self.verification_expiration = datetime.now(timezone.utc) + timedelta(days=1)
        self.save()

    def has_token_limit(self):
        """
        DEPRECATED: Use UserService.has_reached_message_limit() instead.
        """
        warnings.warn(
            "User.has_token_limit() is deprecated. Use UserService.has_reached_message_limit() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.cycle_token_limit is not None

    def has_reached_message_limit(self):
        """
        DEPRECATED: Use UserService.has_reached_message_limit() instead.
        """
        warnings.warn(
            "User.has_reached_message_limit() is deprecated. Use UserService.has_reached_message_limit() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.cycle_token_limit is None:
            return False
        return self.current_cycle_message_count >= self.cycle_token_limit

    def increment_message_count(self):
        """
        DEPRECATED: Use UserService.manage_message_counts() instead.
        """
        warnings.warn(
            "User.increment_message_count() is deprecated. Use UserService.manage_message_counts() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.current_cycle_message_count += 1
        self.total_message_count += 1
        self.save()

    def reset_cycle_message_count(self):
        """
        DEPRECATED: Use UserService.manage_message_counts() instead.
        """
        warnings.warn(
            "User.reset_cycle_message_count() is deprecated. Use UserService.manage_message_counts() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.current_cycle_message_count = 0
        self.save()


# Connect the post_save signal
signals.post_save.connect(lambda sender, document, **kwargs: None, sender=User)
