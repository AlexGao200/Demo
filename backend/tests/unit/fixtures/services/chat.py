import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from models.chat import Chat, Message, CitedSection
from typing import Dict, Any, List


@pytest.fixture
def mock_chat_pdf():
    """Create a mock ChatPDF instance with required methods."""
    mock = Mock()

    # Mock stream_process_query
    async def mock_stream(*args, **kwargs):
        yield {"type": "content", "content": "Test response"}
        yield {
            "type": "citations",
            "cited_sections": [
                {
                    "preview": "Test preview",
                    "title": "Test Document",
                    "document_id": "doc123",
                    "pages": [1, 2],
                    "text": "Full citation text",
                    "extra_data": {},
                    "index_names": ["test_index"],
                    "filter_dimensions": {},
                }
            ],
            "full_text": "Complete response with citations",
        }

    mock.stream_process_query = mock_stream
    mock.generate_chat_title.return_value = "Generated Chat Title"
    return mock


@pytest.fixture
def test_message() -> Dict[str, Any]:
    """Generate test message data."""
    return {
        "sender": "user",
        "content": "Test message",
        "timestamp": datetime.now(timezone.utc),
        "cited_sections": [],
    }


@pytest.fixture
def test_cited_section() -> Dict[str, Any]:
    """Generate test citation data."""
    return {
        "preview": "Test preview",
        "title": "Test Document",
        "document_id": "doc123",
        "pages": [1, 2],
        "text": "Citation text",
        "extra_data": {"key": "value"},
        "index_names": ["test_index"],
        "filter_dimensions": {"dimension": "value"},
        "section_title": "Test Section",
        "file_url": "http://example.com/file",
        "index_display_name": "Test Index",
        "nominal_creator_name": "Test Creator",
        "highlighted_file_url": "http://example.com/highlighted",
    }


@pytest.fixture
def test_chat(test_user) -> Chat:
    """Create a test chat instance."""
    chat = Chat(
        user=test_user,
        title="Test Chat",
        created_at=datetime.now(timezone.utc),
        messages=[],
        is_guest_chat=False,
    )
    chat.save()
    yield chat
    chat.delete()


@pytest.fixture
def test_guest_chat(test_guest_user) -> Chat:
    """Create a test guest chat instance."""
    chat = Chat(
        user=test_guest_user,
        title="Guest Test Chat",
        created_at=datetime.now(timezone.utc),
        messages=[],
        is_guest_chat=True,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        message_limit=50,
        current_message_count=0,
        guest_session_id=f"guest_{test_guest_user.session_id}",
    )
    chat.save()
    yield chat
    chat.delete()


@pytest.fixture
def test_chat_with_messages(test_chat, test_message, test_cited_section) -> Chat:
    """Create a test chat with sample messages."""
    # Add a user message
    user_message = Message(
        sender="user",
        content=test_message["content"],
        timestamp=test_message["timestamp"],
    )

    # Add an AI response with citations
    ai_message = Message(
        sender="ai",
        content="AI response",
        timestamp=datetime.now(timezone.utc),
        cited_sections=[CitedSection(**test_cited_section)],
    )

    test_chat.messages = [user_message, ai_message]
    test_chat.save()
    return test_chat


@pytest.fixture
def test_guest_chat_with_messages(
    test_guest_chat, test_message, test_cited_section
) -> Chat:
    """Create a test guest chat with sample messages."""
    # Add messages similar to regular chat but mark as guest messages
    user_message = Message(
        sender="user",
        content=test_message["content"],
        timestamp=test_message["timestamp"],
        is_guest_message=True,
    )

    ai_message = Message(
        sender="ai",
        content="AI response",
        timestamp=datetime.now(timezone.utc),
        cited_sections=[CitedSection(**test_cited_section)],
        is_guest_message=True,
    )

    test_guest_chat.messages = [user_message, ai_message]
    test_guest_chat.save()
    return test_guest_chat


@pytest.fixture
def chat_service(mock_chat_pdf):
    """Create a ChatService instance with mock dependencies."""
    from services.chat_service import ChatService

    return ChatService(chat_pdf=mock_chat_pdf)


@pytest.fixture
def test_filter_dimensions() -> Dict[str, Any]:
    """Create test filter dimensions."""
    return {"organization": ["org1", "org2"], "department": ["dept1"], "year": ["2024"]}


@pytest.fixture
def test_preset_documents() -> Dict[str, List[str]]:
    """Create test preset documents configuration."""
    return {"titles": ["Document 1", "Document 2"], "index_names": ["index1", "index2"]}


class MockAsyncResponse:
    """Mock async response for streaming tests."""

    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


@pytest.fixture
def mock_stream_response():
    """Create a mock streaming response."""
    chunks = [
        {"type": "content", "content": "Partial response..."},
        {
            "type": "citations",
            "cited_sections": [
                {
                    "preview": "Citation preview",
                    "title": "Source Document",
                    "document_id": "doc123",
                    "pages": [1],
                    "text": "Citation text",
                }
            ],
            "full_text": "Complete response with citation",
        },
    ]
    return MockAsyncResponse(chunks)


# Helper functions for tests
def create_chat_message(
    sender: str,
    content: str,
    timestamp: datetime = None,
    cited_sections: List[Dict] = None,
    is_guest: bool = False,
) -> Message:
    """Create a chat message with optional citations."""
    message = Message(
        sender=sender,
        content=content,
        timestamp=timestamp or datetime.now(timezone.utc),
        is_guest_message=is_guest,
    )

    if cited_sections:
        message.cited_sections = [CitedSection(**cs) for cs in cited_sections]

    return message


def verify_chat_response(response: Dict[str, Any], expected_chat: Chat):
    """Verify chat response structure and content."""
    assert response["id"] == str(expected_chat.id)
    assert response["title"] == expected_chat.title
    assert "createdAt" in response
    assert "messages" in response

    if expected_chat.messages:
        assert len(response["messages"]) == len(expected_chat.messages)
        for resp_msg, exp_msg in zip(response["messages"], expected_chat.messages):
            assert resp_msg["sender"] == exp_msg.sender
            assert resp_msg["content"] == exp_msg.content
            assert "timestamp" in resp_msg
