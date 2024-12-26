from typing import Optional, Any
from providers.anthropic_provider import AnthropicProvider
from providers.groq_provider import GroqProvider
from providers.openai_provider import OpenAICompatibleProvider
from project_types.llm_provider import LLMProvider, RateLimitConfig


class LLMProviderFactory:
    """Factory for creating provider instances"""

    @staticmethod
    def create_provider(
        provider_type: str,
        sync_client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        base_url: Optional[str] = None,
    ) -> LLMProvider:
        """
        Create a provider instance with optional rate limit configuration.
        For testing, you can disable rate limits by passing:
        rate_limit_config=RateLimitConfig(requests_per_minute=0, tokens_per_minute=0, enabled=False)
        """
        if provider_type == "groq":
            return GroqProvider(sync_client, async_client, rate_limit_config)
        elif provider_type == "openai":
            return OpenAICompatibleProvider(
                sync_client, async_client, rate_limit_config, base_url
            )
        elif provider_type == "anthropic":
            return AnthropicProvider(sync_client, async_client, rate_limit_config)
        raise ValueError(f"Unknown provider type: {provider_type}")
