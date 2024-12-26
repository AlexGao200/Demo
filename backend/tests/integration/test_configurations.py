"""Integration tests for LLM configuration objects."""

import pytest
from factories.llm_provider_factory import RateLimitConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="llm_config_tests"),
]


@pytest.mark.test_size("small")
class TestConfigurations:
    """Test suite for configuration objects"""

    def test_rate_limit_configuration(self):
        """Test rate limit configuration setup"""
        config = RateLimitConfig(
            requests_per_minute=30,
            tokens_per_minute=14400,
            enabled=False,  # Disabled for testing
        )
        assert config.requests_per_minute == 30
        assert config.tokens_per_minute == 14400
        assert config.enabled is False

    def test_rate_limit_validation(self):
        """Test rate limit configuration validation"""
        # Test invalid requests per minute
        with pytest.raises(ValueError):
            RateLimitConfig(requests_per_minute=0, tokens_per_minute=14400)

        # Test invalid tokens per minute
        with pytest.raises(ValueError):
            RateLimitConfig(requests_per_minute=30, tokens_per_minute=-1)

    def test_rate_limit_defaults(self):
        """Test rate limit configuration defaults"""
        config = RateLimitConfig(requests_per_minute=30, tokens_per_minute=14400)
        assert config.enabled is True  # Should be enabled by default
