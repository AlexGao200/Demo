"""Factory for creating test-configured service providers with VCR support."""

from typing import Any, Dict, Optional, Tuple, Union
import os
from vcr import VCR
from config.test import TestConfig
from services.llm_service import LLM
from factories.llm_provider_factory import LLMProviderFactory, RateLimitConfig
from factories.embedding_provider_factory import EmbeddingProviderFactory
import cohere
import voyageai
from groq import Groq, AsyncGroq
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic


def get_worker_id() -> str:
    """Get unique worker ID for parallel test execution"""
    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    return f"_{worker}" if worker else ""


def get_cassette_path(cassette_name: str) -> str:
    """Generate unique cassette path for parallel testing"""
    worker_id = get_worker_id()
    base_name, ext = os.path.splitext(cassette_name)
    return f"backend/tests/fixtures/vcr_cassettes/{base_name}{worker_id}{ext}"


def create_vcr_for_test(test_name: str) -> VCR:
    """Create VCR instance with test-specific configuration"""
    record_mode = "once" if os.environ.get("VCR_RECORD_MODE", "0") == "1" else "none"

    return VCR(
        cassette_library_dir=f"backend/tests/fixtures/vcr_cassettes/{test_name}",
        record_mode=record_mode,
        match_on=["method", "scheme", "host", "port", "path", "query", "body"],
        filter_headers=[
            "authorization",
            "Authorization",
            "x-api-key",
            "X-Api-Key",
        ],
        filter_post_data_parameters=[
            "api_key",
            "token",
            "key",
            "secret",
        ],
        decode_compressed_response=True,
        serializer="yaml",
        path_transformer=get_cassette_path,
    )


class TestProviderFactory:
    """Factory for creating test-configured service providers"""

    _provider_instances: Dict[str, Any] = {}
    _test_config: Optional[TestConfig] = None

    @classmethod
    def set_test_config(cls, config: TestConfig):
        """Set the test configuration to use for creating providers"""
        cls._test_config = config

    @classmethod
    def _create_clients(
        cls, provider_type: str, api_key: str, base_url: Optional[str] = None
    ) -> Tuple[Any, Any]:
        """Create sync and async clients for a provider"""
        if provider_type == "groq":
            return (Groq(api_key=api_key), AsyncGroq(api_key=api_key))
        elif provider_type == "openai" or provider_type == "hyperbolic":
            return (
                OpenAI(api_key=api_key, base_url=base_url),
                AsyncOpenAI(api_key=api_key, base_url=base_url),
            )
        elif provider_type == "anthropic":
            return (Anthropic(api_key=api_key), AsyncAnthropic(api_key=api_key))
        elif provider_type == "cohere":
            return (
                cohere.ClientV2(api_key=api_key),
                cohere.AsyncClient(api_key=api_key),
            )
        elif provider_type == "voyage":
            return (
                voyageai.Client(api_key=api_key),
                voyageai.AsyncClient(api_key=api_key),
            )
        raise ValueError(f"Unsupported provider type: {provider_type}")

    @classmethod
    def create_llm_service(
        cls,
        provider_type: str = "groq",
        test_name: str = "default",
        system_prompts: Optional[Union[str, list[Dict[str, Any]]]] = None,
    ) -> LLM:
        """Create LLM service instance with VCR support"""
        if cls._test_config is None:
            raise RuntimeError(
                "TestConfig not set. Ensure setup_test_size fixture runs first."
            )

        provider_key = f"{provider_type}_{test_name}{get_worker_id()}"

        # Return cached provider if available
        if provider_key in cls._provider_instances:
            return cls._provider_instances[provider_key]

        # Provider-specific configurations
        provider_configs = {
            "groq": {
                "api_key": cls._test_config.GROQ_API_KEY,
                "model": "mixtral-8x7b-32768",
                "rate_limits": RateLimitConfig(
                    requests_per_minute=30,
                    tokens_per_minute=14400,
                    enabled=cls._test_config.is_using_real_apis(),
                ),
            },
            "anthropic": {
                "api_key": cls._test_config.ANTHROPIC_API_KEY,
                "model": "claude-3-5-haiku-latest",
                "rate_limits": RateLimitConfig(
                    requests_per_minute=50,
                    tokens_per_minute=100000,
                    enabled=cls._test_config.is_using_real_apis(),
                ),
            },
            "hyperbolic": {
                "api_key": cls._test_config.HYPERBOLIC_API_KEY,
                "model": "meta-llama/Llama-3.2-3B-Instruct",
                "base_url": "https://api.hyperbolic.xyz/v1",
                "rate_limits": RateLimitConfig(
                    requests_per_minute=60,
                    tokens_per_minute=90000,
                    enabled=cls._test_config.is_using_real_apis(),
                ),
            },
        }

        if provider_type not in provider_configs:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        config = provider_configs[provider_type]
        vcr = create_vcr_for_test(test_name)

        with vcr.use_cassette(f"{provider_type}_service_{test_name}.yaml"):
            # Create both sync and async clients
            sync_client, async_client = cls._create_clients(
                provider_type=provider_type
                if provider_type != "hyperbolic"
                else "openai",
                api_key=config["api_key"],
                base_url=config.get("base_url"),
            )

            # Create provider with both clients
            provider = LLMProviderFactory.create_provider(
                provider_type="openai"
                if provider_type == "hyperbolic"
                else provider_type,
                sync_client=sync_client,
                async_client=async_client,
                rate_limit_config=config["rate_limits"],
                base_url=config.get("base_url"),
            )

            # Use provided system prompts or default
            if system_prompts is None:
                if provider_type == "anthropic":
                    # Use structured format for Anthropic
                    system_prompts = [
                        {
                            "type": "text",
                            "text": "You are a helpful assistant for testing.",
                        }
                    ]
                else:
                    # Use simple string for other providers
                    system_prompts = "You are a helpful assistant for testing."

            # Wrap in LLM service
            llm = LLM(
                provider=provider,
                system_prompts=system_prompts,
            )

            cls._provider_instances[provider_key] = llm
            return llm

    @classmethod
    def create_embedding_provider(
        cls, provider_type: str = "cohere", test_name: str = "default"
    ) -> Any:
        """Create embedding model provider with VCR support"""
        if cls._test_config is None:
            raise RuntimeError(
                "TestConfig not set. Ensure setup_test_size fixture runs first."
            )

        provider_key = f"embedding_{provider_type}_{test_name}{get_worker_id()}"

        if provider_key in cls._provider_instances:
            return cls._provider_instances[provider_key]

        # Provider-specific configurations
        provider_configs = {
            "cohere": {
                "api_key": cls._test_config.COHERE_API_KEY,
                "model": "embed-english-v3.0",
                "rate_limits": RateLimitConfig(
                    requests_per_minute=1000,
                    tokens_per_minute=1.5 * 10**8,
                    enabled=cls._test_config.is_using_real_apis(),
                ),
            },
            "voyage": {
                "api_key": cls._test_config.VOYAGE_API_KEY,
                "model": "voyage-multimodal-3",
                "rate_limits": RateLimitConfig(
                    requests_per_minute=1800,
                    tokens_per_minute=1.8 * 10**8,
                    enabled=cls._test_config.is_using_real_apis(),
                ),
            },
        }

        if provider_type not in provider_configs:
            raise ValueError(f"Unsupported embedding provider type: {provider_type}")

        config = provider_configs[provider_type]
        vcr = create_vcr_for_test(test_name)

        with vcr.use_cassette(f"embeddings_{provider_type}_{test_name}.yaml"):
            sync_client, async_client = cls._create_clients(
                provider_type=provider_type,
                api_key=config["api_key"],
            )

            provider = EmbeddingProviderFactory.create_provider(
                provider_type=provider_type,
                sync_client=sync_client,
                async_client=async_client,
                rate_limit_config=config["rate_limits"],
            )

            cls._provider_instances[provider_key] = provider
            return provider
