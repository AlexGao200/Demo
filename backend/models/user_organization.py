from mongoengine import (
    Document,
    ReferenceField,
    StringField,
    DateTimeField,
    BooleanField,
)
from datetime import datetime, timezone


class UserOrganization(Document):
    user = ReferenceField("User", required=True)
    organization = ReferenceField("Organization", required=True)
    role = StringField(choices=["member", "editor", "admin"], required=True)
    is_paid = BooleanField(default=False)
    is_active = BooleanField(default=True)  # Added for soft deletion support
    joined_at = DateTimeField(default=datetime.now(timezone.utc))
    deactivated_at = DateTimeField()  # Added to track when membership was deactivated
    index_name = StringField("", required=True)

    meta = {
        "indexes": [
            "user",
            "organization",
            ("user", "organization"),
            "role",
            "is_active",  # Added index for faster queries
        ]
    }

    def deactivate(self):
        """
        Deactivate the organization membership.
        Used when soft-deleting a user or removing them from an organization.
        """
        self.is_active = False
        self.deactivated_at = datetime.now(timezone.utc)
        self.save()

    @classmethod
    def get_user_organizations(cls, user_id):
        """Get all active organization memberships for a user."""
        return cls.objects(user=user_id, is_active=True)

    @classmethod
    def get_organization_members(cls, organization_id):
        """Get all active members of an organization."""
        return cls.objects(organization=organization_id, is_active=True)

    @classmethod
    def get_user_role_in_organization(cls, user_id, organization_id):
        """Get user's role in an organization if they are an active member."""
        membership = cls.objects(
            user=user_id, organization=organization_id, is_active=True
        ).first()
        return membership.role if membership else None
