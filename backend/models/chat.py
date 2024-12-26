from datetime import datetime, timezone
from typing import Optional, Tuple
from mongoengine import (
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
    DictField,
    BooleanField,
)


class CitedSection(EmbeddedDocument):
    """
    Represents a cited section within a message.

    This embedded document provides schema validation for critical citation fields
    while allowing for additional flexible data storage.

    Attributes:
        preview (str): A preview or snippet of the cited section.
        title (str): The title of the document or section being cited.
        document_id (str): An identifier for the document containing the cited section.
        pages (List[str]): A list of page numbers where the cited section appears.
        extra_data (dict): A flexible field for storing additional, unstructured citation data.
        index_names (List[str]): A list of index names associated with the cited section.
        filter_dimensions (dict): A dictionary of filter dimensions applied to the citation.
        section_title (str): The title of the specific section being cited.
        file_url (str): The URL of the file containing the cited section.
        text (str): The full text of the cited section.
    """

    preview = StringField(required=True)
    title = StringField(required=True)
    document_id = StringField(required=True)
    pages = ListField(IntField(), required=True)
    extra_data = DictField()
    index_names = ListField(StringField())
    filter_dimensions = DictField()
    section_title = StringField()
    file_url = StringField()
    text = StringField(required=True)
    index_display_name = StringField()
    nominal_creator_name = StringField()
    highlighted_file_url = StringField()


class Message(EmbeddedDocument):
    """
    Represents a single message in a chat conversation.

    Attributes:
        sender (str): The sender of the message. Must be either "user" or "ai".
        content (str): The content of the message.
        timestamp (datetime): The time when the message was sent. Defaults to the current UTC time.
        cited_sections (List[CitedSection]): A list of cited sections in the message.
        is_guest_message (bool): Flag indicating if message was sent during a guest session.
                              Used for analytics and potential future feature differentiation.
    """

    sender = StringField(choices=["user", "ai"], required=True)
    content = StringField(required=True)
    timestamp = DateTimeField(default=datetime.now(timezone.utc))
    cited_sections = EmbeddedDocumentListField(CitedSection)
    is_guest_message = BooleanField(default=False)  # New field


class Chat(Document):
    """
    Represents a chat conversation in the application.

    Attributes:
        user (ReferenceField): Reference to the User who owns this chat. For guest chats,
                             references a temporary guest user.
        title (str): The title of the chat conversation.
        messages (List[Message]): A list of Message documents representing the conversation.
        created_at (datetime): The time when the chat was created. Defaults to current UTC time.
        updated_at (datetime): The time when the chat was last updated. Defaults to current UTC time.
        filter_organizations (List[ReferenceField]): References to Organization documents if the chat
                                                   is filtered by organizations. Not used for guest chats.

        Guest-specific attributes (optional):
        is_guest_chat (bool): Indicates if this is a guest chat session.
        expires_at (datetime): When this guest chat expires and should be cleaned up.
        message_limit (int): Maximum number of messages allowed in this guest chat.
        current_message_count (int): Number of messages currently in this guest chat.
        guest_session_id (str): Reference to the guest session this chat belongs to.

    Meta:
        collection (str): Specifies the name of the MongoDB collection for this document.
        indexes (list): Defines database indexes for optimizing queries, including:
                       - Compound index on user and created_at for efficient sorting
                       - Index on guest-specific fields for cleanup operations
                       - Index on guest_session_id for session management

    Note:
        - Regular chats: The 'filter_organizations' field allows for organization-specific
          filtering, useful for access control and query specificity.
        - Guest chats: Additional fields track session state and enforce limits. These
          chats are temporary and will be automatically cleaned up after expiration.
    """

    # Core fields
    user = ReferenceField("User", required=True)
    title = StringField(required=True)
    messages = EmbeddedDocumentListField(Message)
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))
    filter_organizations = ListField(ReferenceField("Organization"), default=None)

    # Guest-specific fields (all optional)
    is_guest_chat = BooleanField(default=False)
    expires_at = DateTimeField(required=False)
    message_limit = IntField(required=False)
    current_message_count = IntField(default=0, required=False)
    guest_session_id = StringField(required=False)  # Links chat to guest session

    # For QR Chat
    preset_documents = DictField(required=False)

    meta = {
        "collection": "chats",
        "indexes": [
            {"fields": ["user", "created_at"]},
            # New indexes for guest chat management
            {"fields": ["is_guest_chat", "expires_at"]},  # For cleanup operations
            {"fields": ["guest_session_id"]},  # For session management
            {
                "fields": ["is_guest_chat", "guest_session_id", "created_at"]
            },  # For guest chat retrieval
        ],
    }

    def should_filter_by_documents(self) -> bool:
        """Check if this chat should filter by specific documents."""
        return bool(self.preset_documents and self.preset_documents.get("titles"))

    def get_document_filter(self) -> Tuple[Optional[list[str]], Optional[list[str]]]:
        """Get the document titles and indices if they exist."""
        if not self.preset_documents:
            return None, None
        return (
            self.preset_documents.get("titles"),
            self.preset_documents.get("index_names", []),
        )

    def increment_message_count(self):
        """
        Increment the message count for guest chats and check limits.

        Returns:
            bool: True if message was counted, False if limit reached

        Note:
            Only applies to guest chats. Regular chats always return True.
        """
        if not self.is_guest_chat:
            return True

        if self.current_message_count >= self.message_limit:
            return False

        self.current_message_count += 1
        self.save()
        return True

    def is_expired(self) -> bool:
        """
        Check if this chat has expired (guest chats only).

        Returns:
            bool: True if chat is expired or is a guest chat past expiration,
                 False for regular chats or valid guest chats
        """
        if not self.is_guest_chat:
            return False

        return self.expires_at and datetime.now(timezone.utc) > self.expires_at
