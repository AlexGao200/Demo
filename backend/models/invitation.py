from mongoengine import (
    Document,
    StringField,
    ReferenceField,
    BooleanField,
    DateTimeField,
    EmailField,
)
from datetime import datetime, timezone
from models.user import User
from models.organization import Organization


class Invitation(Document):
    organization = ReferenceField("Organization", required=True)
    token = StringField(required=True)
    sent_at = DateTimeField(required=True)
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    accepted = BooleanField(default=False)
    user = ReferenceField(User)
    email = EmailField(required=True)

    meta = {
        "indexes": [
            "token",  # Index on the token field for fast lookup
            "email",  # Index on email for faster lookups
            "created_at",  # Index on created_at for sorting and filtering
        ]
    }


class RegistrationCode(Document):
    code = StringField(required=True)
    organization = ReferenceField(Organization, required=True)
    membership_type = StringField(required=True, choices=["paid", "free"])
    created_at = DateTimeField(default=datetime.now(timezone.utc))

    meta = {
        "indexes": [
            "code",  # Index on code for fast lookup
            "organization",  # Index on organization for faster queries
        ]
    }

    def __str__(self):
        return f"Code: {self.code}, Organization: {self.organization.name}, Membership Type: {self.membership_type}"
