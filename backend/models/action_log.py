from datetime import datetime, timezone
from mongoengine import DateTimeField, Document, ListField, ReferenceField, StringField


class ActionLog(Document):
    """
    ActionLog model for tracking and auditing user actions within the application.

    This model is designed to log various actions performed by users, providing
    a comprehensive audit trail for both organization admins and superadmins.
    It captures details such as the user who performed the action, the type of action,
    related documents, users, and organizations affected by the action, and the timestamp.

    Fields:
    - originating_user: Reference to the User who performed the action
    - action_type: Type of action performed (e.g., upload_doc, invite_user)
    - target_documents: List of documents affected by the action (if applicable)
    - target_users: List of users affected by the action (if applicable)
    - target_indices: List of indices affected by the action (if applicable)
    - target_orgs: List of organizations affected by the action (if applicable)
    - timestamp: Date and time when the action was performed
    - description: Additional details about the action

    Usage:
    - Create a new log entry when a significant action is performed in the system
    - Query log entries for auditing purposes, user activity tracking, or system analysis
    - Aggregate log data for generating reports or insights on system usage

    Note:
    This model is suitable for basic logging and auditing needs. For high-volume logging
    or complex querying requirements, consider supplementing this with specialized
    logging solutions like ELK stack or Prometheus for system-wide metrics.
    """

    originating_user = ReferenceField("User", required=True)
    action_type = StringField(
        required=True,
        choices=[
            "upload_doc",
            "delete_doc",
            "modify_doc",
            "invite_user",
            "remove_user_from_org",
            "upgrade_user",
            "downgrade_user",
            "create_org",
            "delete_org",
            "add_member",
            "join_org",
            "leave_org",
            "update_user_role",
            "audit_logs",
            "transfer_ownership",
            "approve_doc_petition",
            "reject_doc_petition",
            "generate_registration_code",
            "submit_join_request",
            "handle_join_request",
        ],
    )
    target_documents = ListField(ReferenceField("FileMetadata"), required=False)
    target_users = ListField(ReferenceField("User"), required=False)
    target_indices = ListField(ReferenceField("IndexRegistry"), required=False)
    target_orgs = ListField(ReferenceField("Organization"), required=False)
    timestamp = DateTimeField(default=datetime.now(timezone.utc))
    description = StringField(required=False)

    meta = {"collection": "action_logs"}

    def __str__(self):
        """
        String representation of the ActionLog instance.

        Returns:
        str: A human-readable string describing the log entry
        """
        return f"ActionLog: {self.action_type} by {self.originating_user} at {self.timestamp}"

    @classmethod
    def log_action(
        cls,
        originating_user,
        action_type,
        target_documents=None,
        target_users=None,
        target_indices=None,
        target_orgs=None,
        description=None,
    ):
        """
        Create and save a new ActionLog entry.

        Args:
        originating_user (User): The user performing the action
        action_type (str): The type of action being performed
        target_documents (list, optional): List of affected documents
        target_users (list, optional): List of affected users
        target_indices (list, optional): List of affected indices
        target_orgs (list, optional): List of affected organizations
        description (str, optional): Additional details about the action

        Returns:
        ActionLog: The created and saved ActionLog instance

        Raises:
        ValueError: If the action_type is not in the predefined choices
        """
        if action_type not in cls.action_type.choices:
            raise ValueError(f"Invalid action_type: {action_type}")

        log_entry = cls(
            originating_user=originating_user,
            action_type=action_type,
            target_documents=target_documents or [],
            target_users=target_users or [],
            target_indices=target_indices or [],
            target_orgs=target_orgs or [],
            description=description or "",
        )
        log_entry.save()
        return log_entry

    @classmethod
    def get_user_actions(cls, originating_user, start_date=None, end_date=None):
        """
        Retrieve action logs for a specific user within an optional date range.

        Args:
        originating_user (User): The user whose actions to retrieve
        start_date (datetime, optional): The start date of the date range
        end_date (datetime, optional): The end date of the date range

        Returns:
        QuerySet: A queryset of ActionLog instances matching the criteria
        """
        query = cls.objects(originating_user=originating_user)
        if start_date:
            query = query.filter(timestamp__gte=start_date)
        if end_date:
            query = query.filter(timestamp__lte=end_date)
        return query.order_by("-timestamp")

    @classmethod
    def get_org_actions(cls, org, start_date=None, end_date=None):
        """
        Retrieve action logs for a specific organization within an optional date range.

        Args:
        org (Organization): The organization whose actions to retrieve
        start_date (datetime, optional): The start date of the date range
        end_date (datetime, optional): The end date of the date range

        Returns:
        QuerySet: A queryset of ActionLog instances matching the criteria
        """
        query = cls.objects(target_orgs=org)
        if start_date:
            query = query.filter(timestamp__gte=start_date)
        if end_date:
            query = query.filter(timestamp__lte=end_date)
        return query.order_by("-timestamp")
