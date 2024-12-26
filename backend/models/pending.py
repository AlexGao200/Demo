from mongoengine import Document, StringField, ReferenceField, DateTimeField
from models.user import User
from datetime import datetime, timezone


class PendingDocument(Document):
    title = StringField(required=True)
    file_url = StringField(required=True)  # In s3
    status = StringField(required=True, default="pending")
    from_user = ReferenceField(User, required=True)
    target_organization = ReferenceField("Organization", required=True)
    fallback_organization = ReferenceError("Organization")

    meta = {"collection": "pending_documents"}


class PendingRequest(Document):
    user = ReferenceField("User", required=True)  # User making the request
    first_name = StringField(required=True)  # User's first name
    last_name = StringField(required=True)  # User's last name
    organization = ReferenceField(
        "Organization", required=True
    )  # Organization the request is for
    request_message = StringField()  # Optional message from the user
    status = StringField(
        default="pending", choices=["pending", "approved", "declined"]
    )  # Status of the request
    created_at = DateTimeField(default=datetime.now(timezone.utc))  # Timestamp

    meta = {"collection": "pending_requests"}

    def __str__(self):
        return f"Request by {self.user.username} to join {self.organization.name}"
