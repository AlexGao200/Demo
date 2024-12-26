import pytest
from unittest.mock import patch
import json
from datetime import datetime, timezone, timedelta
from blueprints.chat_routes import create_chat_blueprint


@pytest.fixture
def chat_bp(chat_service, mock_limiter):
    """Create the chat blueprint with dependencies."""
    return create_chat_blueprint(chat_service, mock_limiter)


@pytest.fixture
def chat_app(minimal_app, chat_bp):
    """Configure test app with chat blueprint."""
    minimal_app.register_blueprint(chat_bp)
    return minimal_app


class TestChatRoutes:
    """Test suite for chat routes."""

    async def test_create_regular_chat(self, chat_app, regular_auth_headers, test_user):
        """Test creating a chat for regular user."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/chat", json={"time_zone": "UTC"}, headers=regular_auth_headers
            )

            assert response.status_code == 201
            data = response.get_json()
            assert "chat_id" in data
            assert not data.get("is_guest", False)
            assert "expires_at" not in data
            assert "message_limit" not in data

    async def test_create_guest_chat(self, chat_app, guest_auth_headers):
        """Test creating a chat for guest user."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/chat", json={"time_zone": "UTC"}, headers=guest_auth_headers
            )

            assert response.status_code == 201
            data = response.get_json()
            assert "chat_id" in data
            assert data["is_guest"]
            assert "expires_at" in data
            assert "message_limit" in data
            assert "guest_session_id" in data

    async def test_create_chat_with_preset_documents(
        self, chat_app, regular_auth_headers, test_preset_documents
    ):
        """Test creating a chat with preset document filters."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/chat",
                json={"time_zone": "UTC", "preset_documents": test_preset_documents},
                headers=regular_auth_headers,
            )

            assert response.status_code == 201
            data = response.get_json()
            assert "preset_documents" in data
            assert data["preset_documents"] == test_preset_documents
            assert "Chat about:" in data["title"]

    async def test_get_chat_history_regular_user(
        self, chat_app, regular_auth_headers, test_chat_with_messages
    ):
        """Test retrieving chat history for regular user."""
        async with chat_app.test_client() as client:
            response = await client.get(
                f"/api/chat_history?chat_id={test_chat_with_messages.id}",
                headers=regular_auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2  # Two messages from test_chat_with_messages
            assert data[0]["sender"] == "user"
            assert data[1]["sender"] == "ai"
            assert "cited_sections" in data[1]

    async def test_get_chat_history_guest_user(
        self, chat_app, guest_auth_headers, test_guest_chat_with_messages
    ):
        """Test retrieving chat history for guest user."""
        async with chat_app.test_client() as client:
            response = await client.get(
                f"/api/chat_history?chat_id={test_guest_chat_with_messages.id}",
                headers=guest_auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2
            for message in data:
                if message["sender"] == "ai":
                    assert "cited_sections" in message

    async def test_get_chat_history_unauthorized(
        self, chat_app, regular_auth_headers, test_guest_chat_with_messages
    ):
        """Test unauthorized access to chat history."""
        async with chat_app.test_client() as client:
            response = await client.get(
                f"/api/chat_history?chat_id={test_guest_chat_with_messages.id}",
                headers=regular_auth_headers,
            )

            assert response.status_code == 403
            assert "Access denied" in response.get_json()["error"]

    async def test_ask_stream_regular_user(
        self, chat_app, regular_auth_headers, test_chat, mock_stream_response
    ):
        """Test streaming chat response for regular user."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/ask_stream",
                json={
                    "query": "test question",
                    "chat_id": str(test_chat.id),
                    "indices": ["test_index"],
                    "filter_dimensions": {},
                },
                headers=regular_auth_headers,
            )

            assert response.status_code == 200
            assert response.headers["Content-Type"] == "text/event-stream"

            chunks = []
            async for chunk in response.response:
                if chunk.startswith(b"data: "):
                    event = json.loads(chunk.decode().split("data: ")[1])
                    chunks.append(event)

            assert len(chunks) > 0
            assert any(chunk["type"] == "content" for chunk in chunks)
            assert any(chunk["type"] == "citations" for chunk in chunks)

    async def test_ask_stream_guest_user(
        self, chat_app, guest_auth_headers, test_guest_chat, mock_stream_response
    ):
        """Test streaming chat response for guest user."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/ask_stream",
                json={"query": "test question", "chat_id": str(test_guest_chat.id)},
                headers=guest_auth_headers,
            )

            assert response.status_code == 200

            chunks = []
            async for chunk in response.response:
                if chunk.startswith(b"data: "):
                    event = json.loads(chunk.decode().split("data: ")[1])
                    chunks.append(event)

            assert len(chunks) > 0
            assert test_guest_chat.current_message_count == 1

    async def test_ask_stream_with_filters(
        self, chat_app, regular_auth_headers, test_chat, test_filter_dimensions
    ):
        """Test streaming with filter dimensions."""
        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/ask_stream",
                json={
                    "query": "test question",
                    "chat_id": str(test_chat.id),
                    "filter_dimensions": test_filter_dimensions,
                },
                headers=regular_auth_headers,
            )

            assert response.status_code == 200
            # Verify filters were applied (check logs or mock calls)

    async def test_guest_session_expiration(
        self, chat_app, guest_auth_headers, test_guest_chat
    ):
        """Test handling of expired guest sessions."""
        # Set session to expired
        test_guest_chat.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        test_guest_chat.save()

        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/ask_stream",
                json={"query": "test question", "chat_id": str(test_guest_chat.id)},
                headers=guest_auth_headers,
            )

            assert response.status_code == 200
            chunks = [chunk async for chunk in response.response]
            first_chunk = chunks[0]
            event = json.loads(first_chunk.decode().split("data: ")[1])
            assert event["type"] == "error"
            assert "expired" in event["message"].lower()

    async def test_rate_limiting(self, chat_app, regular_auth_headers, test_chat):
        """Test rate limiting on ask endpoint."""
        async with chat_app.test_client() as client:
            responses = []
            for _ in range(11):  # Limit is 10 per minute
                response = await client.post(
                    "/api/ask_stream",
                    json={"query": "test question", "chat_id": str(test_chat.id)},
                    headers=regular_auth_headers,
                )
                responses.append(response.status_code)

            assert 429 in responses
            assert responses.count(200) == 10

    async def test_chat_sessions(
        self, chat_app, regular_auth_headers, test_user, test_chat_with_messages
    ):
        """Test retrieving chat sessions."""
        async with chat_app.test_client() as client:
            response = await client.get(
                "/api/chat_sessions", headers=regular_auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert len(data) > 0
            assert all(key in data[0] for key in ["id", "title", "createdAt"])

    @pytest.mark.parametrize("missing_field", ["query", "chat_id"])
    async def test_ask_stream_missing_fields(
        self, chat_app, regular_auth_headers, test_chat, missing_field
    ):
        """Test handling of missing required fields."""
        payload = {"query": "test question", "chat_id": str(test_chat.id)}
        del payload[missing_field]

        async with chat_app.test_client() as client:
            response = await client.post(
                "/api/ask_stream", json=payload, headers=regular_auth_headers
            )

            assert response.status_code == 200  # SSE connection successful
            chunks = [chunk async for chunk in response.response]
            first_chunk = chunks[0]
            event = json.loads(first_chunk.decode().split("data: ")[1])
            assert event["type"] == "error"
            assert event["status"] == 400

    @pytest.mark.parametrize(
        "error_type,expected_message",
        [
            ("connection_error", "Failed to connect"),
            ("timeout_error", "Request timed out"),
            ("validation_error", "Invalid input"),
        ],
    )
    async def test_error_handling(
        self, chat_app, regular_auth_headers, test_chat, error_type, expected_message
    ):
        """Test handling of various error conditions."""
        with patch(
            "services.chat_service.ChatService.ask_question_stream"
        ) as mock_stream:
            mock_stream.side_effect = Exception(expected_message)

            # Use test_client() without async context manager
            client = chat_app.test_client()
            response = await client.post(
                "/api/ask_stream",
                json={"query": "test question", "chat_id": str(test_chat.id)},
                headers=regular_auth_headers,
            )

            assert response.status_code == 200
            chunks = []
            async for chunk in response.response:
                if chunk.startswith(b"data: "):
                    event = json.loads(chunk.decode().split("data: ")[1])
                    chunks.append(event)

            assert len(chunks) > 0
            assert chunks[0]["type"] == "error"
            assert expected_message in chunks[0]["message"]

    async def test_guest_message_limit(
        self, chat_app, guest_auth_headers, test_guest_chat
    ):
        """Test guest message limit enforcement."""
        test_guest_chat.message_limit = 1
        test_guest_chat.save()

        async with chat_app.test_client() as client:
            # First message (should succeed)
            response1 = await client.post(
                "/api/ask_stream",
                json={"query": "first question", "chat_id": str(test_guest_chat.id)},
                headers=guest_auth_headers,
            )
            assert response1.status_code == 200

            # Second message (should fail)
            response2 = await client.post(
                "/api/ask_stream",
                json={"query": "second question", "chat_id": str(test_guest_chat.id)},
                headers=guest_auth_headers,
            )

            chunks = [chunk async for chunk in response2.response]
            first_chunk = chunks[0]
            event = json.loads(first_chunk.decode().split("data: ")[1])
            assert event["type"] == "error"
            assert "limit" in event["message"].lower()
