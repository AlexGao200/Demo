"""Integration tests for LLM service layer."""

import pytest
from project_types.llm_provider import ProviderResponse
from typing import Iterator, AsyncIterator
from tests.integration.conftest import test_stats
import asyncio

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="llm_service_tests"),
]

# Define providers and their model configurations
PROVIDER_CONFIGS = [
    ("groq", "mixtral-8x7b-32768"),
    ("anthropic", "claude-3-5-haiku-latest"),
    ("openai", "meta-llama/Meta-Llama-3.1-405B-Instruct"),
]


@pytest.fixture
def test_query():
    """Simple test query for LLM interactions"""
    return "What is the capital of France?"


@pytest.fixture
def expected_response():
    """Expected response pattern for the test query"""
    return "Paris"


@pytest.fixture(params=PROVIDER_CONFIGS)
def provider_setup(request):
    """Provider configuration fixture"""
    provider_type, model_id = request.param
    return {
        "provider_type": provider_type,
        "model_id": model_id,
    }


@pytest.mark.test_size("medium")
class TestLLMService:
    """Test suite for LLM service functionality."""

    def test_basic_generation(
        self, llm_service, test_query, expected_response, provider_setup
    ):
        """Test basic generation through service layer."""
        test_stats.record_api_call(f"service_basic_{provider_setup['provider_type']}")

        response = llm_service.invoke(
            query=test_query,
            model_id=provider_setup["model_id"],
            system_prompt="You are a helpful assistant. Be concise.",
        )

        assert isinstance(response, ProviderResponse)
        assert expected_response in response.content
        assert response.total_tokens > 0
        assert response.input_tokens > 0
        assert response.output_tokens > 0
        assert response.total_tokens == response.input_tokens + response.output_tokens

    def test_streaming(
        self, llm_service, test_query, expected_response, provider_setup
    ):
        """Test streaming functionality."""
        test_stats.record_api_call(
            f"service_streaming_{provider_setup['provider_type']}"
        )

        stream = llm_service.invoke(
            query=test_query,
            model_id=provider_setup["model_id"],
            stream=True,
            system_prompt="You are a helpful assistant. Be concise.",
        )

        assert isinstance(stream, Iterator)
        response_text = "".join(chunk for chunk in stream)
        assert expected_response in response_text

    @pytest.mark.asyncio
    async def test_async_generation(
        self, llm_service, test_query, expected_response, provider_setup
    ):
        """Test async generation."""
        test_stats.record_api_call(
            f"async_generation_{provider_setup['provider_type']}"
        )

        response = await llm_service.ainvoke(
            query=test_query,
            model_id=provider_setup["model_id"],
            system_prompt="You are a helpful assistant. Be concise.",
        )

        assert isinstance(response, ProviderResponse)
        assert expected_response in response.content
        assert response.total_tokens > 0
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_async_streaming(
        self, llm_service, test_query, expected_response, provider_setup
    ):
        """Test async streaming functionality."""
        test_stats.record_api_call(f"async_streaming_{provider_setup['provider_type']}")

        stream = await llm_service.ainvoke(
            query=test_query,
            model_id=provider_setup["model_id"],
            stream=True,
            system_prompt="You are a helpful assistant. Be concise.",
        )

        assert isinstance(stream, AsyncIterator)
        response_chunks = []
        async for chunk in stream:
            response_chunks.append(chunk)

        response_text = "".join(response_chunks)
        assert expected_response in response_text

    def test_system_prompt_handling(self, llm_service, provider_setup):
        """Test system prompt variations."""
        test_stats.record_api_call(f"system_prompt_{provider_setup['provider_type']}")

        prompts = [
            "You are a helpful assistant that speaks formally.",
            "You are a helpful assistant that speaks casually.",
            "You are a helpful assistant that speaks technically.",
        ]

        query = "Explain what a database is."
        responses = []

        for prompt in prompts:
            response = llm_service.invoke(
                query=query, model_id=provider_setup["model_id"], system_prompt=prompt
            )
            responses.append(response.content)

        # Verify responses are different (influenced by system prompt)
        assert len(set(responses)) == len(
            prompts
        ), "System prompts should influence response style"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, llm_service, provider_setup):
        """Test concurrent request handling."""
        test_stats.record_api_call(f"concurrent_{provider_setup['provider_type']}")

        queries = ["What is Python?", "What is JavaScript?", "What is Rust?"]

        # Make concurrent requests
        tasks = [
            llm_service.ainvoke(
                query=query,
                model_id=provider_setup["model_id"],
                system_prompt="Be concise.",
            )
            for query in queries
        ]

        responses = await asyncio.gather(*tasks)

        assert all(isinstance(r, ProviderResponse) for r in responses)
        assert all(len(r.content) > 0 for r in responses)
        assert all(r.total_tokens > 0 for r in responses)
        assert all(r.input_tokens > 0 for r in responses)
        assert all(r.output_tokens > 0 for r in responses)
        assert all(
            r.total_tokens == r.input_tokens + r.output_tokens for r in responses
        )

        # Verify responses are different (no cross-contamination)
        response_texts = [r.content for r in responses]
        assert len(set(response_texts)) == len(
            queries
        ), "Each query should have a unique response"

    def test_error_handling(self, llm_service, provider_setup):
        """Test service-level error handling."""
        test_stats.record_api_call(f"service_error_{provider_setup['provider_type']}")

        # Test empty query
        with pytest.raises(Exception):
            llm_service.invoke(query="", model_id=provider_setup["model_id"])

        # Test missing model ID
        with pytest.raises(Exception):
            llm_service.invoke(query="test", model_id="")

        # Test invalid system prompt
        with pytest.raises(Exception):
            llm_service.invoke(
                query="test", model_id=provider_setup["model_id"], system_prompt=""
            )

    def test_token_control(self, llm_service, provider_setup):
        """Test token limit controls."""
        test_stats.record_api_call(f"token_control_{provider_setup['provider_type']}")

        query = "Tell me everything you know about artificial intelligence."

        # Test with explicit max_tokens
        response = llm_service.invoke(
            query=query,
            model_id=provider_setup["model_id"],
            system_prompt="Write a very long response about AI.",
            max_tokens=50,
        )
        assert isinstance(response, ProviderResponse)
        assert response.output_tokens <= 50

        # Test without max_tokens (should use provider defaults)
        response_default = llm_service.invoke(
            query=query,
            model_id=provider_setup["model_id"],
            system_prompt="Write a very long response about AI.",
        )
        assert isinstance(response_default, ProviderResponse)
        assert len(response_default.content) > len(response.content)
