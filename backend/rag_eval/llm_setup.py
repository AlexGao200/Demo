import os
from environs import Env
from groq import Groq, AsyncGroq
from deepeval.models import DeepEvalBaseLLM
from services.elasticsearch_service import create_elasticsearch_client_with_retries
import cohere
import voyageai
import voyageai.client_async
from services.embedding_service import EmbeddingModel
from factories.embedding_provider_factory import EmbeddingProviderFactory
from utils.error_handlers import log_error
import openai
import anthropic
from providers.groq_provider import GroqProvider
from providers.openai_provider import OpenAICompatibleProvider
from providers.anthropic_provider import AnthropicProvider
from services.rag import GenerationStrategy


class ProviderAdapter(DeepEvalBaseLLM):
    """Adapter to make our providers compatible with DeepEval's interface"""

    def __init__(
        self, provider, model_id: str, supported_strategies: list[GenerationStrategy]
    ):
        self.provider = provider
        self.model_id = model_id
        self.supported_strategies = supported_strategies

    def get_model_name(self) -> str:
        return f"{type(self.provider).__name__}_{self.model_id}"

    def load_model(self):
        return self.provider

    def generate(self, prompt: str) -> str:
        try:
            response = self.provider.generate(
                messages=[{"role": "user", "content": prompt}],
                model_id=self.model_id,
                temperature=0.5,
                max_tokens=1024,
            )
            return response.content
        except Exception as e:
            log_error(e, "Error in generation")
            return ""

    async def a_generate(self, prompt: str) -> str:
        try:
            response = await self.provider.agenerate(
                messages=[{"role": "user", "content": prompt}],
                model_id=self.model_id,
                temperature=0.5,
                max_tokens=1024,
            )
            return response.content
        except Exception as e:
            log_error(e, "Error in async generation")
            return ""


def setup_environment():
    """Initialize all required services and models."""
    print("Setting up environment and services...")

    env = Env()
    env.read_env()
    print("✓ Environment variables loaded")

    clients = []

    # Setup Groq (text-only models)
    groq_sync = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    groq_async = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    groq_provider = GroqProvider(
        sync_client=groq_sync,
        async_client=groq_async,
    )
    groq_models = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]
    for model in groq_models:
        clients.append(
            ProviderAdapter(
                groq_provider,
                model,
                supported_strategies=[GenerationStrategy.TEXT_ONLY],
            )
        )
    print("✓ Groq client initialized")

    # Setup Hyperbolic
    hyperbolic_sync = openai.OpenAI(
        base_url="https://api.hyperbolic.xyz/v1",
        api_key=os.environ.get("HYPERBOLIC_API_KEY"),
    )
    hyperbolic_async = openai.AsyncOpenAI(
        base_url="https://api.hyperbolic.xyz/v1",
        api_key=os.environ.get("HYPERBOLIC_API_KEY"),
    )
    hyperbolic_provider = OpenAICompatibleProvider(
        sync_client=hyperbolic_sync,
        async_client=hyperbolic_async,
        base_url="https://api.hyperbolic.xyz/v1",
    )

    # Text-only models
    hyperbolic_text_models = [
        "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
    ]

    for model in hyperbolic_text_models:
        clients.append(
            ProviderAdapter(
                hyperbolic_provider,
                model,
                supported_strategies=[GenerationStrategy.TEXT_ONLY],
            )
        )

    # Vision models
    hyperbolic_vision_models = [
        "Qwen/Qwen2-VL-72B-Instruct",
        "meta-llama/Llama-3.2-3B-Instruct",
    ]

    for model in hyperbolic_vision_models:
        clients.append(
            ProviderAdapter(
                hyperbolic_provider,
                model,
                supported_strategies=[
                    GenerationStrategy.IMAGES_ONLY,
                    GenerationStrategy.INTERLEAVED,
                ],
            )
        )
    print("✓ Hyperbolic clients initialized")

    # Setup Anthropic
    anthropic_sync = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    anthropic_async = anthropic.AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    anthropic_provider = AnthropicProvider(
        sync_client=anthropic_sync,
        async_client=anthropic_async,
    )

    # Text-only models
    anthropic_text_models = [
        "claude-3-5-haiku-latest",
    ]

    for model in anthropic_text_models:
        clients.append(
            ProviderAdapter(
                anthropic_provider,
                model,
                supported_strategies=[GenerationStrategy.TEXT_ONLY],
            )
        )

    # Vision models
    anthropic_vision_models = [
        "claude-3-5-sonnet-latest",
        "claude-3-opus-latest",
    ]

    for model in anthropic_vision_models:
        clients.append(
            ProviderAdapter(
                anthropic_provider,
                model,
                supported_strategies=[
                    GenerationStrategy.IMAGES_ONLY,
                    GenerationStrategy.INTERLEAVED,
                ],
            )
        )
    print("✓ Anthropic clients initialized")

    # Create elasticsearch client with environment variables
    es_client = create_elasticsearch_client_with_retries(
        host=os.getenv("ELASTICSEARCH_HOST", "localhost"),
        port=int(os.getenv("ELASTICSEARCH_PORT", 9200)),
    )
    print("✓ Elasticsearch client initialized")

    # Initialize embedding providers using the factory
    embeddings_providers = {
        "cohere": EmbeddingModel(
            EmbeddingProviderFactory.create_provider(
                "cohere",
                sync_client=cohere.Client(api_key=os.getenv("COHERE_API_KEY")),
                async_client=cohere.AsyncClient(api_key=os.getenv("COHERE_API_KEY")),
            )
        ),
        "voyage": EmbeddingModel(
            EmbeddingProviderFactory.create_provider(
                "voyage",
                sync_client=voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY")),
                async_client=voyageai.AsyncClient(api_key=os.getenv("VOYAGE_API_KEY")),
            )
        ),
    }
    print("✓ Embedding providers initialized")

    return clients, es_client, embeddings_providers
