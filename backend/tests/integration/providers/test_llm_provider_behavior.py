"""Integration tests for LLM provider behavior and constraints."""

import pytest
from project_types.llm_provider import ProviderResponse, RateLimitError
from tests.integration.conftest import test_stats
import asyncio

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="llm_behavior_tests"),
]

# Define providers and their model configurations
PROVIDER_CONFIGS = [
    ("groq", "mixtral-8x7b-32768"),
    ("anthropic", "claude-3-5-haiku-latest"),
    ("openai", "meta-llama/Meta-Llama-3.1-405B-Instruct"),
]


@pytest.fixture(params=PROVIDER_CONFIGS)
def provider_setup(request):
    """Provider configuration fixture"""
    provider_type, model_id = request.param
    return {
        "provider_type": provider_type,
        "model_id": model_id,
    }


@pytest.mark.test_size("medium")
class TestProviderBehavior:
    """Test suite for provider behavior and constraints."""

    def test_rate_limiting(self, llm_service, provider_setup):
        """Test rate limiting behavior."""
        test_stats.record_api_call(f"rate_limiting_{provider_setup['provider_type']}")

        # Test rapid requests within rate limits
        responses = []
        for _ in range(3):  # Reduced to 3 requests to stay within rate limits
            test_stats.record_api_call(
                f"rate_limiting_{provider_setup['provider_type']}"
            )
            response = llm_service.invoke(
                query="Say 'test' and nothing else.",
                model_id=provider_setup["model_id"],
                system_prompt="Be very concise.",
            )
            responses.append(response)

        assert all(isinstance(r, ProviderResponse) for r in responses)
        assert all("test" in r.content.strip().lower() for r in responses)
        assert all(r.total_tokens > 0 for r in responses)
        assert all(r.input_tokens > 0 for r in responses)
        assert all(r.output_tokens > 0 for r in responses)

    def test_token_limits(self, llm_service, provider_setup):
        """Test token limit handling."""
        test_stats.record_api_call(f"token_limits_{provider_setup['provider_type']}")

        query = "Tell me everything you know about artificial intelligence."
        system_prompt = "Write a very long response about AI."

        # Test with explicit max_tokens
        response = llm_service.invoke(
            query=query,
            model_id=provider_setup["model_id"],
            system_prompt=system_prompt,
            max_tokens=50,
        )
        assert isinstance(response, ProviderResponse)
        assert response.output_tokens <= 50
        assert response.total_tokens == response.input_tokens + response.output_tokens

        # Test without max_tokens (should use provider defaults)
        response_default = llm_service.invoke(
            query=query,
            model_id=provider_setup["model_id"],
            system_prompt=system_prompt,
        )
        assert isinstance(response_default, ProviderResponse)
        assert len(response_default.content) > len(response.content)
        assert (
            response_default.total_tokens
            == response_default.input_tokens + response_default.output_tokens
        )

    def test_error_handling(self, llm_service, provider_setup):
        """Test provider error scenarios."""
        test_stats.record_api_call(f"error_handling_{provider_setup['provider_type']}")

        # Test empty query
        with pytest.raises(Exception):
            llm_service.invoke(query="", model_id=provider_setup["model_id"])

        # Test invalid model ID
        with pytest.raises(Exception):
            llm_service.invoke(query="test", model_id="invalid-model-id")

        # Test empty system prompt
        with pytest.raises(Exception):
            llm_service.invoke(
                query="test", model_id=provider_setup["model_id"], system_prompt=""
            )

    def test_retry_behavior(self, llm_service, provider_setup):
        """Test retry mechanisms."""
        test_stats.record_api_call(f"retry_behavior_{provider_setup['provider_type']}")

        # Force rate limit to test retry
        try:
            # Make rapid requests to trigger rate limit
            for _ in range(10):
                llm_service.invoke(
                    query="Test retry mechanism",
                    model_id=provider_setup["model_id"],
                    system_prompt="Be concise.",
                )
        except RateLimitError:
            # Expected rate limit error
            pass

        # Verify we can still make requests after waiting
        import time

        time.sleep(5)  # Wait for rate limit to reset

        response = llm_service.invoke(
            query="Test retry mechanism",
            model_id=provider_setup["model_id"],
            system_prompt="Be concise.",
        )
        assert isinstance(response, ProviderResponse)
        assert response.content.strip() != ""
        assert response.total_tokens > 0
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_concurrent_rate_limits(self, llm_service, provider_setup):
        """Test rate limiting under concurrent load."""
        test_stats.record_api_call(
            f"concurrent_rate_limits_{provider_setup['provider_type']}"
        )

        async def make_request():
            return await llm_service.ainvoke(
                query="Quick test",
                model_id=provider_setup["model_id"],
                system_prompt="Be concise.",
            )

        async def run_concurrent_requests(n):
            tasks = [make_request() for _ in range(n)]
            return await asyncio.gather(*tasks, return_exceptions=True)

        # Run multiple requests concurrently
        results = await run_concurrent_requests(3)

        # Check that at least some requests succeeded
        successful_responses = [r for r in results if isinstance(r, ProviderResponse)]
        assert len(successful_responses) > 0

        # Verify token tracking for successful responses
        for response in successful_responses:
            assert response.total_tokens > 0
            assert response.input_tokens > 0
            assert response.output_tokens > 0
            assert (
                response.total_tokens == response.input_tokens + response.output_tokens
            )

    def test_provider_specific_behavior(self, llm_service, provider_setup):
        """Test provider-specific behaviors and constraints."""
        test_stats.record_api_call(
            f"provider_specific_{provider_setup['provider_type']}"
        )

        # Test response consistency
        responses = []
        for _ in range(2):
            response = llm_service.invoke(
                query="What is 2+2?",
                model_id=provider_setup["model_id"],
                system_prompt="Be a precise calculator.",
                temperature=0.0,  # Set temperature to 0 for deterministic output
            )
            responses.append(response.content.strip())

        # Verify responses are consistent with temperature=0
        assert (
            responses[0] == responses[1]
        ), "Responses should be consistent with temperature=0"

        # Test temperature variation
        varied_responses = []
        for _ in range(2):
            response = llm_service.invoke(
                query="Tell me a random number between 1 and 100",
                model_id=provider_setup["model_id"],
                system_prompt="Be creative.",
                temperature=1.0,  # Set high temperature for variation
            )
            varied_responses.append(response.content.strip())

        # Verify responses vary with high temperature
        assert (
            varied_responses[0] != varied_responses[1]
        ), "Responses should vary with temperature=1.0"
