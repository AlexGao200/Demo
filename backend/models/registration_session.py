from mongoengine import (
    BooleanField,
    EmbeddedDocument,
    EmailField,
    Document,
    EmbeddedDocumentField,
    IntField,
    DateTimeField,
    StringField,
)
from datetime import datetime, timedelta, timezone
import secrets


class RegistrationSteps(EmbeddedDocument):
    email_verified = BooleanField(default=False)
    identity_completed = BooleanField(default=False)
    organization_completed = BooleanField(default=False)


class RegistrationSession(Document):
    email = EmailField(required=True)
    registration_steps = EmbeddedDocumentField(
        RegistrationSteps, default=RegistrationSteps
    )
    verification_code = StringField(min_length=6, max_length=6)
    verification_token = StringField()
    verification_attempt_expiry = DateTimeField(required=True)
    attempts = IntField(default=0, min_value=0, max_value=5)
    created_at = DateTimeField(default=datetime.now(timezone.utc))

    meta = {
        "collection": "registration_sessions",
        "indexes": [
            # TTL index to auto-expire sessions after 24 hours
            {"fields": ["created_at"], "expireAfterSeconds": 24 * 60 * 60},
            # Index for quick email lookups
            {"fields": ["email"], "unique": True, "sparse": True},
            # Compound index for verification
            {
                "fields": ["verification_code", "verification_attempt_expiry"],
                "sparse": True,
            },
        ],
        # Optional but recommended for startups - helps catch errors early
        "strict": True,
    }

    @classmethod
    def create_session(cls, email: str) -> "RegistrationSession":
        """Factory method to create a new registration session."""
        return cls(
            email=email,
            verification_code=secrets.randbelow(1000000).__str__().zfill(6),
            verification_attempt_expiry=datetime.now(timezone.utc)
            + timedelta(minutes=15),
        ).save()

    def refresh_verification_code(self) -> None:
        """Generate a new verification code and reset expiry."""
        self.verification_code = secrets.randbelow(1000000).__str__().zfill(6)
        self.verification_attempt_expiry = datetime.now(timezone.utc) + timedelta(
            minutes=15
        )
        self.save()

    def verify_code(self, code: str) -> bool:
        """Verify the provided code and update status if correct."""
        if self.verification_code == code and self.verification_attempt_expiry.replace(
            tzinfo=timezone.utc
        ) > datetime.now(timezone.utc):
            self.registration_steps.email_verified = True
            self.save()
            return True
        self.attempts += 1
        self.save()
        return False

    def verify_token(self, token: str) -> bool:
        """Verify the provided token and update status if correct."""
        if (
            self.verification_token == token
            and self.verification_attempt_expiry
            and self.verification_attempt_expiry.replace(tzinfo=timezone.utc)
            > datetime.now(timezone.utc)
        ):
            self.registration_steps.email_verified = True
            self.save()
            return True
        self.attempts += 1
        self.save()
        return False

    def complete_identity_step(self) -> None:
        """Mark the identity step as completed."""
        self.registration_steps.identity_completed = True
        self.save()

    def complete_organization_step(self) -> None:
        """Mark the organization step as completed."""
        self.registration_steps.organization_completed = True
        self.save()

    def is_registration_complete(self) -> bool:
        """Check if all registration steps are completed."""
        steps = self.registration_steps
        return all(
            [
                steps.email_verified,
                steps.identity_completed,
                steps.organization_completed,
            ]
        )
