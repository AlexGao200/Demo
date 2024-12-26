from typing import Optional, Any
from providers.cohere_provider import CohereProvider
from providers.voyage_provider import VoyageProvider
from project_types.embedding_provider import EmbeddingProvider
from project_types.provider_limiter import RateLimitConfig


class EmbeddingProviderFactory:
    """Factory for creating embedding provider instances"""

    @staticmethod
    def create_provider(
        provider_type: str,
        sync_client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ) -> EmbeddingProvider:
        """
        Create an embedding provider instance with optional rate limit configuration.
        For testing, you can disable rate limits by passing:
        rate_limit_config=RateLimitConfig(requests_per_minute=0, tokens_per_minute=0, enabled=False)

        Args:
            provider_type: The type of provider to create ("cohere" or "voyage")
            sync_client: Optional synchronous client instance
            async_client: Optional asynchronous client instance
            rate_limit_config: Optional rate limiting configuration

        Returns:
            An instance of the specified embedding provider

        Raises:
            ValueError: If an unknown provider type is specified
        """
        if provider_type == "cohere":
            return CohereProvider(sync_client, async_client, rate_limit_config)
        elif provider_type == "voyage":
            return VoyageProvider(sync_client, async_client, rate_limit_config)
        raise ValueError(f"Unknown embedding provider type: {provider_type}")
