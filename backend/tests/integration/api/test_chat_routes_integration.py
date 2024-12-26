import pytest
import json
import asyncio
from datetime import datetime, timezone

from models.chat import Chat


@pytest.fixture
def test_chat(registered_user):
    """Create a test chat instance."""
    chat = Chat(
        user=registered_user,
        title="Test Chat",
        created_at=datetime.now(timezone.utc),
        messages=[],
    ).save()
    yield chat
    # Ensure cleanup
    Chat.objects(id=chat.id).delete()


@pytest.fixture
def mock_llm_response():
    """Fixture for consistent LLM responses in small tests."""
    return {
        "content": "This is a test response",
        "citations": [{"text": "Test citation", "metadata": {"page": 1}}],
    }


@pytest.mark.blueprints(["chat"])
@pytest.mark.asyncio
class TestChatRoutes:
    """Integration tests for chat routes."""

    @pytest.mark.test_size("small")
    async def test_chat_creation(
        self, integration_client, auth_headers, registered_user
    ):
        """Test basic chat creation and validation."""
        # Test with minimal required data
        create_response = await integration_client.post(
            "/api/chat", json={"time_zone": "UTC"}, headers=auth_headers
        )
        assert create_response.status_code == 201
        assert "chat_id" in create_response.json
        chat_id = create_response.json["chat_id"]

        # Verify chat creation in database
        chat = Chat.objects(id=chat_id).first()
        assert chat is not None
        assert str(chat.user.id) == str(registered_user.id)
        assert chat.title is not None
        assert chat.created_at is not None
        assert isinstance(chat.messages, list)
        assert len(chat.messages) == 0

        # Test with optional data
        create_response = await integration_client.post(
            "/api/chat",
            json={"time_zone": "America/New_York", "title": "Custom Title"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        chat_id = create_response.json["chat_id"]
        chat = Chat.objects(id=chat_id).first()
        assert chat.title == "Custom Title"

    @pytest.mark.test_size("medium")
    async def test_chat_lifecycle(
        self, integration_client, auth_headers, registered_user
    ):
        """Test complete chat lifecycle from creation to history retrieval."""
        # Create chat
        create_response = await integration_client.post(
            "/api/chat", json={"time_zone": "UTC"}, headers=auth_headers
        )
        assert create_response.status_code == 201
        chat_id = create_response.json["chat_id"]

        # Send query
        query = "What is the meaning of life?"
        query_response = await integration_client.post(
            "/api/ask_stream",
            json={
                "query": query,
                "chat_id": chat_id,
                "indices": ["test_index"],
            },
            headers=auth_headers,
        )
        assert query_response.status_code == 200

        # Process streamed response
        response_text = ""
        citations = None
        error = None

        async def process_stream():
            nonlocal response_text, citations, error
            try:
                async for chunk in query_response.iter_chunks():
                    if not chunk:
                        continue
                    if not chunk.startswith(b"data: "):
                        continue

                    try:
                        data = json.loads(chunk[6:])
                        chunk_type = data.get("type")

                        if chunk_type == "content":
                            response_text += data.get("text", "")
                        elif chunk_type == "citations":
                            citations = data.get("cited_sections", [])
                            # Citations are the last chunk, we can break here
                            break
                        elif chunk_type == "error":
                            error = data.get("text")
                            break
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                error = str(e)

        # Set timeout for stream processing
        try:
            await asyncio.wait_for(process_stream(), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail("Stream processing timed out")

        # Check for errors first
        if error:
            pytest.fail(f"Error during stream processing: {error}")

        # Verify we got a response
        assert response_text.strip(), "No response text received"

        # Citations are optional but if present should be properly formatted
        if citations:
            assert isinstance(citations, list), "Citations should be a list"
            for citation in citations:
                assert "text" in citation, "Citation missing text field"
                assert "file_url" in citation, "Citation missing file_url field"

        # Verify chat history
        history_response = await integration_client.get(
            f"/api/chat_history?chat_id={chat_id}", headers=auth_headers
        )
        assert history_response.status_code == 200
        history = history_response.json
        assert len(history) >= 2  # At least user query and assistant response
        assert history[0]["sender"] == "user"
        assert history[0]["content"] == query
        assert history[1]["sender"] == "assistant"
        assert history[1]["content"].strip()

        # Verify message persistence
        chat = Chat.objects(id=chat_id).first()
        assert len(chat.messages) >= 2
        assert chat.messages[0].content == query
        assert chat.messages[0].sender == "user"
        assert chat.messages[1].sender == "assistant"
        assert chat.messages[1].content.strip()

    @pytest.mark.test_size("large")
    async def test_concurrent_chat_sessions(self, integration_client, auth_headers):
        """Test handling multiple concurrent chat sessions."""
        NUM_SESSIONS = 3
        NUM_MESSAGES_PER_SESSION = 2

        # Create multiple chat sessions
        chat_ids = []
        for _ in range(NUM_SESSIONS):
            response = await integration_client.post(
                "/api/chat", json={"time_zone": "UTC"}, headers=auth_headers
            )
            assert response.status_code == 201
            chat_ids.append(response.json["chat_id"])

        # Send queries to all sessions concurrently
        async def query_chat(chat_id, message_num):
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "query": f"Test query {message_num} for chat {chat_id}",
                    "chat_id": chat_id,
                    "indices": ["test_index"],
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

            # Process stream
            response_text = ""
            error = None

            try:
                async for chunk in response.iter_chunks():
                    if not chunk or not chunk.startswith(b"data: "):
                        continue
                    try:
                        data = json.loads(chunk[6:])
                        chunk_type = data.get("type")

                        if chunk_type == "content":
                            response_text += data.get("text", "")
                        elif chunk_type == "citations":
                            # Got citations, stream is complete
                            break
                        elif chunk_type == "error":
                            error = data.get("text")
                            break
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                error = str(e)

            if error:
                return False

            return bool(response_text.strip())

        # Send multiple messages to each chat concurrently
        all_tasks = []
        for chat_id in chat_ids:
            for msg_num in range(NUM_MESSAGES_PER_SESSION):
                all_tasks.append(query_chat(chat_id, msg_num))

        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(asyncio.gather(*all_tasks), timeout=30.0)
            assert all(results), "Some queries failed to receive complete responses"
        except asyncio.TimeoutError:
            pytest.fail("Concurrent chat processing timed out")

        # Verify all chat histories
        for chat_id in chat_ids:
            history_response = await integration_client.get(
                f"/api/chat_history?chat_id={chat_id}", headers=auth_headers
            )
            assert history_response.status_code == 200
            history = history_response.json
            assert (
                len(history) >= NUM_MESSAGES_PER_SESSION * 2
            )  # User messages + responses

    @pytest.mark.test_size("small")
    @pytest.mark.parametrize(
        "error_case",
        [
            ("invalid_chat_id", {"chat_id": "invalid_id"}),
            ("missing_query", {"chat_id": "valid_id", "query": ""}),
            (
                "invalid_indices",
                {"chat_id": "valid_id", "query": "test", "indices": "not_a_list"},
            ),
            ("empty_indices", {"chat_id": "valid_id", "query": "test", "indices": []}),
            ("invalid_timezone", {"time_zone": "Invalid/TZ"}),
        ],
    )
    async def test_error_handling(
        self, integration_client, auth_headers, error_case, test_chat
    ):
        """Test various error scenarios."""
        case_name, params = error_case

        if case_name == "invalid_chat_id":
            response = await integration_client.get(
                f"/api/chat_history?chat_id={params['chat_id']}", headers=auth_headers
            )
            assert response.status_code == 404
            assert "error" in response.json

        elif case_name == "missing_query":
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "chat_id": str(test_chat.id),
                    "query": params["query"],
                    "indices": ["test_index"],
                },
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "error" in response.json

        elif case_name == "invalid_indices":
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "chat_id": str(test_chat.id),
                    "query": params["query"],
                    "indices": params["indices"],
                },
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "error" in response.json

        elif case_name == "empty_indices":
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "chat_id": str(test_chat.id),
                    "query": params["query"],
                    "indices": params["indices"],
                },
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "error" in response.json

        elif case_name == "invalid_timezone":
            response = await integration_client.post(
                "/api/chat",
                json={"time_zone": params["time_zone"]},
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "error" in response.json

    @pytest.mark.test_size("medium")
    async def test_rate_limiting(self, integration_client, auth_headers, monkeypatch):
        """Test rate limiting functionality."""
        # Configure deterministic rate limits
        REQUESTS_PER_MINUTE = 2

        class MockLimiter:
            def __init__(self, *args, **kwargs):
                self.count = 0
                self.limit = REQUESTS_PER_MINUTE

            def test_limit(self, *args, **kwargs):
                self.count += 1
                return self.count <= self.limit

        monkeypatch.setattr("flask_limiter.Limiter", MockLimiter)

        # Create a chat for testing
        create_response = await integration_client.post(
            "/api/chat", json={"time_zone": "UTC"}, headers=auth_headers
        )
        chat_id = create_response.json["chat_id"]

        # Test rate limiting
        responses = []
        for i in range(REQUESTS_PER_MINUTE + 1):
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "query": f"Test query {i}",
                    "chat_id": chat_id,
                    "indices": ["test_index"],
                },
                headers=auth_headers,
            )
            responses.append(response.status_code)

        assert responses.count(200) == REQUESTS_PER_MINUTE
        assert responses.count(429) == 1
        assert responses[-1] == 429  # Last request should be rate limited

    @pytest.mark.test_size("medium")
    async def test_chat_persistence(
        self, integration_client, auth_headers, registered_user
    ):
        """Test chat persistence and data integrity."""
        # Create initial chat
        create_response = await integration_client.post(
            "/api/chat", json={"time_zone": "UTC"}, headers=auth_headers
        )
        chat_id = create_response.json["chat_id"]

        # Send a series of messages
        messages = ["First test message", "Second test message", "Third test message"]

        for msg in messages:
            response = await integration_client.post(
                "/api/ask_stream",
                json={
                    "query": msg,
                    "chat_id": chat_id,
                    "indices": ["test_index"],
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

            # Process stream
            response_text = ""
            error = None

            try:
                async for chunk in response.iter_chunks():
                    if not chunk or not chunk.startswith(b"data: "):
                        continue
                    try:
                        data = json.loads(chunk[6:])
                        chunk_type = data.get("type")

                        if chunk_type == "content":
                            response_text += data.get("text", "")
                        elif chunk_type == "citations":
                            # Got citations, stream is complete
                            break
                        elif chunk_type == "error":
                            error = data.get("text")
                            break
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                error = str(e)

            if error:
                pytest.fail(f"Error during stream processing: {error}")
            assert response_text.strip(), "Empty response received"

        # Verify persistence in database
        chat = Chat.objects(id=chat_id).first()
        assert chat is not None
        assert (
            len(chat.messages) >= len(messages) * 2
        )  # Each message should have a response

        # Verify message ordering and content
        user_messages = [msg for msg in chat.messages if msg.sender == "user"]
        assert len(user_messages) >= len(messages)
        for sent, stored in zip(messages, user_messages):
            assert stored.content == sent

        # Verify assistant responses
        assistant_messages = [msg for msg in chat.messages if msg.sender == "assistant"]
        assert len(assistant_messages) >= len(messages)
        for msg in assistant_messages:
            assert msg.content.strip()
            assert msg.created_at is not None

    @pytest.mark.test_size("small")
    async def test_authorization(self, integration_client):
        """Test authorization requirements for chat endpoints."""
        endpoints = [
            ("POST", "/api/chat", {}),
            ("GET", "/api/chat_history", {"chat_id": "123"}),
            (
                "POST",
                "/api/ask_stream",
                {"query": "test", "chat_id": "123", "indices": ["test"]},
            ),
            ("GET", "/api/chat_sessions", {}),
        ]

        for method, endpoint, data in endpoints:
            if method == "GET":
                response = await integration_client.get(
                    endpoint + "?" + "&".join(f"{k}={v}" for k, v in data.items())
                )
            else:
                response = await integration_client.post(endpoint, json=data)

            assert (
                response.status_code in (401, 403)
            ), f"Expected 401 or 403 for unauthorized {method} {endpoint}, got {response.status_code}"
            assert "error" in response.json

    @pytest.mark.test_size("small")
    async def test_input_validation(self, integration_client, auth_headers, test_chat):
        """Test input validation for various endpoints."""
        test_cases = [
            {
                "endpoint": "/api/chat",
                "method": "POST",
                "data": {"time_zone": "Invalid/Timezone"},
                "expected_status": 400,
                "error_check": lambda r: "time_zone" in r.json.get("error", "").lower(),
            },
            {
                "endpoint": "/api/ask_stream",
                "method": "POST",
                "data": {
                    "query": "",  # Empty query
                    "chat_id": str(test_chat.id),
                    "indices": ["test_index"],
                },
                "expected_status": 400,
                "error_check": lambda r: "query" in r.json.get("error", "").lower(),
            },
            {
                "endpoint": "/api/ask_stream",
                "method": "POST",
                "data": {
                    "query": "Valid query",
                    "chat_id": "",  # Empty chat_id
                    "indices": ["test_index"],
                },
                "expected_status": 400,
                "error_check": lambda r: "chat" in r.json.get("error", "").lower(),
            },
            {
                "endpoint": "/api/ask_stream",
                "method": "POST",
                "data": {
                    "query": "Valid query",
                    "chat_id": str(test_chat.id),
                    "indices": [],  # Empty indices
                },
                "expected_status": 400,
                "error_check": lambda r: "indices" in r.json.get("error", "").lower(),
            },
        ]

        for case in test_cases:
            if case["method"] == "GET":
                response = await integration_client.get(
                    case["endpoint"], headers=auth_headers
                )
            else:
                response = await integration_client.post(
                    case["endpoint"], json=case["data"], headers=auth_headers
                )

            assert (
                response.status_code == case["expected_status"]
            ), f"Expected {case['expected_status']} for {case['method']} {case['endpoint']}, got {response.status_code}"
            assert "error" in response.json
            assert case[
                "error_check"
            ](
                response
            ), f"Error message validation failed for {case['method']} {case['endpoint']}"
