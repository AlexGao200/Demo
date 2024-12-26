"""Unit tests for the EmbeddingProviderFactory."""

import pytest
from unittest.mock import MagicMock

from factories.embedding_provider_factory import EmbeddingProviderFactory
from providers.cohere_provider import CohereProvider
from providers.voyage_provider import VoyageProvider
from project_types.provider_limiter import RateLimitConfig


@pytest.fixture
def mock_clients():
    """Create mock sync and async clients."""
    return MagicMock(), MagicMock()


@pytest.fixture
def rate_limit_config():
    """Create a test rate limit configuration."""
    return RateLimitConfig(
        requests_per_minute=60,
        tokens_per_minute=1000,
        enabled=True,
    )


def test_create_cohere_provider(mock_clients, rate_limit_config):
    """Test creation of Cohere provider."""
    sync_client, async_client = mock_clients
    provider = EmbeddingProviderFactory.create_provider(
        provider_type="cohere",
        sync_client=sync_client,
        async_client=async_client,
        rate_limit_config=rate_limit_config,
    )

    assert isinstance(provider, CohereProvider)
    assert provider.sync_client == sync_client
    assert provider.async_client == async_client
    assert provider.rate_limit_config == rate_limit_config
    assert provider.provider_type == "cohere"


def test_create_voyage_provider(mock_clients, rate_limit_config):
    """Test creation of Voyage provider."""
    sync_client, async_client = mock_clients
    provider = EmbeddingProviderFactory.create_provider(
        provider_type="voyage",
        sync_client=sync_client,
        async_client=async_client,
        rate_limit_config=rate_limit_config,
    )

    assert isinstance(provider, VoyageProvider)
    assert provider.sync_client == sync_client
    assert provider.async_client == async_client
    assert provider.rate_limit_config == rate_limit_config
    assert provider.provider_type == "voyage"


def test_create_provider_invalid_type(mock_clients, rate_limit_config):
    """Test error handling for invalid provider type."""
    sync_client, async_client = mock_clients
    with pytest.raises(ValueError) as exc_info:
        EmbeddingProviderFactory.create_provider(
            provider_type="invalid",
            sync_client=sync_client,
            async_client=async_client,
            rate_limit_config=rate_limit_config,
        )
    assert "Unknown embedding provider type: invalid" in str(exc_info.value)


def test_create_provider_without_rate_limits(mock_clients):
    """Test provider creation without rate limit config."""
    sync_client, async_client = mock_clients
    provider = EmbeddingProviderFactory.create_provider(
        provider_type="cohere",
        sync_client=sync_client,
        async_client=async_client,
    )

    assert provider.rate_limit_config is not None
    assert provider.rate_limit_config.requests_per_minute > 0
    assert provider.rate_limit_config.tokens_per_minute > 0


def test_create_provider_without_clients():
    """Test provider creation without clients."""
    provider = EmbeddingProviderFactory.create_provider(
        provider_type="cohere",
    )

    assert provider.sync_client is None
    assert provider.async_client is None
    assert provider.rate_limit_config is not None
