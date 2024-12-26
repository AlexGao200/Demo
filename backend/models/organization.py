from mongoengine import DateTimeField, Document, StringField, BooleanField
from datetime import datetime, timezone
import uuid
from slugify import slugify

from models.file_metadata import FileMetadata


class Organization(Document):
    index_name = StringField(unique=True, required=True)
    name = StringField(required=True)
    slug_name = StringField(required=True, unique=True)
    email_suffix = StringField()
    password = StringField(required=True)
    organization_contract = StringField(choices=["active", "inactive"])
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))
    billing_cycle_start = DateTimeField()
    billing_cycle_end = DateTimeField()
    stripe_customer_id = StringField()
    has_public_documents = BooleanField(default=False)

    meta = {
        "indexes": [
            "index_name",
            "slug_name",
            "email_suffix",
            "organization_contract",
            "has_public_documents",
            ("name", "email_suffix"),
        ]
    }

    def update_public_documents_status(self):
        # Get all organizations from the FileMetadata that have this organization associated
        public_docs_exist = (
            FileMetadata.objects(organizations=self, visibility="public")
            .limit(1)
            .count()
            > 0
        )

        # Update has_public_documents based on whether there are public documents or not
        self.has_public_documents = public_docs_exist
        self.save()

    def get_members_by_role(self, role):
        from models.user_organization import UserOrganization

        memberships = UserOrganization.objects(organization=self.id, role=role)
        return [membership.user for membership in memberships]

    def get_member_role(self, user_id):
        from models.user_organization import UserOrganization

        membership = UserOrganization.objects(
            organization=self.id, user=user_id
        ).first()
        return membership.role if membership else None

    def is_editor(self, user_id):
        role = self.get_member_role(user_id)
        return role in ["editor", "admin"]

    def add_member(self, user, role, is_paid=False):
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=user.id, organization=self.id).update_one(
            set__role=role, set__is_paid=is_paid, upsert=True
        )

    def update_member_role(self, user_id, new_role):
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=user_id, organization=self.id).update_one(
            set__role=new_role
        )

    def remove_member(self, user_id):
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=user_id, organization=self.id).delete()

    def has_valid_contract(self):
        """Check if an organization has a valid contract."""
        return self.organization_contract == "active"

    def activate_contract(self):
        """Change an organization's contract status to active."""
        self.organization_contract = "active"
        self.save()

    def deactivate_contract(self):
        """Deactivate an organization's contract status."""
        self.organization_contract = "inactive"
        self.save()

    def add_paid_member(self, user):
        """Add a user to the list of the organization's paid members."""
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=user.id, organization=self.id).update_one(
            set__is_paid=True, upsert=True
        )

    def remove_paid_member(self, user_id):
        """Remove the paid status from a member"""
        from models.user_organization import UserOrganization

        UserOrganization.objects(user=user_id, organization=self.id).update_one(
            set__is_paid=False
        )

    def is_paid_member(self, user_id):
        """Check if a user is a paid member of the organization"""
        from models.user_organization import UserOrganization

        membership = UserOrganization.objects(
            user=user_id, organization=self.id
        ).first()
        return membership.is_paid if membership else False

    def clean(self):
        """Called automatically before saving"""
        if not self.index_name:
            # Generate a temporary index name that matches the format used in create_organization
            slug = self.slug_name or slugify(self.name)
            self.index_name = f"temp_{slug}_{uuid.uuid4().hex[:8]}"
