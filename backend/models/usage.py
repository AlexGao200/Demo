# backend/models/user.py
from datetime import datetime, timezone

from mongoengine import (
    DateTimeField,
    Document,
    StringField,
    ReferenceField,
    IntField,
)


class TokenUsage(Document):
    user = ReferenceField("User", required=True)
    organization = ReferenceField("Organization", required=True)
    timestamp = DateTimeField(default=datetime.now(timezone.utc))
    tokens_used = IntField(required=True)
    feature = StringField(choices=["embedding", "rag", "other"])
    document_id = StringField()  # If applicable
    query_context = StringField()  # Brief description or ID of the query

    meta = {
        "indexes": [
            ("user", "organization", "timestamp"),
            ("organization", "timestamp"),
        ]
    }

    @staticmethod
    def get_total_token_usage(org_id, billing_cycle_start, billing_cycle_end):
        return TokenUsage.objects(
            organization=org_id,
            timestamp__gte=billing_cycle_start,
            timestamp__lte=billing_cycle_end,
        ).sum("tokens_used")
