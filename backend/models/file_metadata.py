from datetime import datetime, timezone
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
    URLField,
    DictField,
    FloatField,
)


class ProcessingStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileMetadata(Document):
    name = StringField(required=True)
    s3_url = StringField(required=True)
    document_hash = StringField(required=True)
    title = StringField(required=True)
    index_names = ListField(required=True)
    thumbnail_urls = ListField(URLField())
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    visibility = StringField(required=True, choices=["public", "private"])
    originating_user = ReferenceField("User", required=True)
    organizations = ListField(ReferenceField("Organization"))
    nominal_creator_name = StringField(required=False)
    index_display_name = StringField(required=True)
    filter_dimensions = DictField(required=False)
    is_deleted = BooleanField(default=False)

    # Processing status fields
    processing_status = StringField(
        required=True,
        choices=[
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ],
        default=ProcessingStatus.PENDING,
    )
    processing_progress = FloatField(min_value=0.0, max_value=1.0, default=0.0)
    processing_step = StringField()  # Current processing step description
    processing_error = StringField()
    processing_started_at = DateTimeField()
    processing_completed_at = DateTimeField()

    meta = {
        "collection": "file_metadata",
        "indexes": [
            "name",
            "document_hash",
            "index_names",
            "originating_user",
            "organizations",
            "filter_dimensions",
            "processing_status",  # Add index for status queries
        ],
    }

    def update_progress(self, progress: float, step: str = None):
        """
        Update processing progress and optionally the current step.

        Args:
            progress: Float between 0 and 1 indicating progress
            step: Optional description of current processing step
        """
        self.processing_progress = min(max(progress, 0.0), 1.0)
        if step:
            self.processing_step = step
        self.save()
