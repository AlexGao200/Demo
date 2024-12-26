"""Integration tests for embedding providers with VCR."""

import pytest
from PIL import Image
import numpy as np
import io
import base64
import os
import vcr
from project_types.embedding_provider import EmbeddingResponse
from project_types.error_types import (
    RateLimitError,
    AuthenticationError,
    InvalidRequestError,
)
from factories.embedding_provider_factory import EmbeddingProviderFactory
from project_types.provider_limiter import RateLimitConfig


# Configure VCR for API recording/replay
def get_vcr_path(provider_type, test_name):
    """Get the path for VCR cassettes based on provider and test name."""
    cassette_dir = os.path.join(os.path.dirname(__file__), "cassettes", provider_type)
    os.makedirs(cassette_dir, exist_ok=True)
    return os.path.join(cassette_dir, f"{test_name}.yaml")


def create_test_image(color="red"):
    """Create a test image for embedding tests."""
    return Image.new("RGB", (224, 224), color=color)


def get_base64_image(image):
    """Convert PIL Image to base64 string."""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()
    return base64.b64encode(img_byte_arr).decode()


@pytest.mark.test_size("medium")
class TestEmbeddingProviders:
    """Comprehensive integration tests for embedding providers.

    Design Philosophy:
    - Tests are provider-agnostic by default but can be provider-specific when needed
    - Focuses on real-world usage patterns important for a seed startup
    - Validates core functionality, error handling, and performance characteristics
    - Uses VCR for reliable, fast test execution while maintaining real API behavior
    """

    @pytest.fixture(autouse=True)
    def setup(self, embedding_provider, request):
        """Setup test fixtures and provider-specific configurations."""
        self.provider = embedding_provider
        self.model_id = (
            "embed-english-v3.0"
            if self.provider.provider_type == "cohere"
            else "voyage-multimodal-3"
        )

        # Configure VCR for this test
        test_name = request.node.name
        vcr_path = get_vcr_path(self.provider.provider_type, test_name)

        self.vcr = vcr.VCR(
            cassette_library_dir=os.path.dirname(vcr_path),
            record_mode="new_episodes",
            match_on=["method", "scheme", "host", "port", "path", "query", "body"],
            filter_headers=["authorization"],
            filter_post_data_parameters=["api_key"],
        )

    def test_provider_factory_validation(self):
        """Test provider factory error handling."""
        with pytest.raises(ValueError, match="Unknown embedding provider type"):
            EmbeddingProviderFactory.create_provider("invalid_provider")

    @pytest.mark.provider_type("cohere")
    def test_text_embedding_cohere(self):
        """Test text embedding generation with Cohere."""
        with self.vcr.use_cassette("cohere_text_embedding.yaml"):
            inputs = ["This is a test sentence.", "Another test sentence."]
            response = self.provider.embed(inputs=inputs, model_id=self.model_id)

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == len(inputs)
            assert all(isinstance(emb, list) for emb in response.embeddings)
            assert all(
                isinstance(val, float) for emb in response.embeddings for val in emb
            )
            assert response.input_type == "text"
            assert response.model_id == self.model_id

    @pytest.mark.provider_type("voyage")
    def test_text_embedding_voyage(self):
        """Test text embedding generation with Voyage."""
        with self.vcr.use_cassette("voyage_text_embedding.yaml"):
            inputs = ["This is a test sentence.", "Another test sentence."]
            response = self.provider.embed(inputs=inputs, model_id=self.model_id)

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == len(inputs)
            assert all(isinstance(emb, list) for emb in response.embeddings)
            assert all(
                isinstance(val, float) for emb in response.embeddings for val in emb
            )
            assert response.input_type == "text"
            assert response.model_id == self.model_id

    @pytest.mark.provider_type("voyage")
    def test_multimodal_embedding_voyage(self):
        """Test multimodal embedding with mixed input types."""
        with self.vcr.use_cassette("voyage_multimodal_embedding.yaml"):
            img = create_test_image()
            inputs = [
                ("A description of an image", img),
                "Text only input",
                img,
            ]

            response = self.provider.embed(inputs=inputs, model_id=self.model_id)

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == 3
            assert response.input_type == "multimodal"

    @pytest.mark.asyncio
    @pytest.mark.provider_type("cohere")
    async def test_async_operations_cohere(self):
        """Test async embedding operations with Cohere."""
        with self.vcr.use_cassette("cohere_async_embedding.yaml"):
            inputs = ["Async test input", "Another async test"]

            response = await self.provider.async_embed(
                inputs=inputs, model_id=self.model_id
            )

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == len(inputs)
            assert response.input_type == "text"

    @pytest.mark.asyncio
    @pytest.mark.provider_type("voyage")
    async def test_async_operations_voyage(self):
        """Test async embedding operations with Voyage."""
        with self.vcr.use_cassette("voyage_async_embedding.yaml"):
            img = create_test_image()
            inputs = [
                "Async text input",
                img,
                ("Text with image", img),
            ]

            response = await self.provider.async_embed(
                inputs=inputs, model_id=self.model_id
            )

            assert isinstance(response, EmbeddingResponse)
            assert response.embeddings is not None
            assert response.input_type == "multimodal"

    @pytest.mark.asyncio
    async def test_async_batch_operations(self):
        """Test async batch embedding operations."""
        with self.vcr.use_cassette("batch_async_embedding.yaml"):
            # Create a mix of text and image inputs
            inputs = [
                "First text input",
                "Final text input",
            ]

            response = await self.provider.async_embed(
                inputs=inputs, model_id=self.model_id
            )

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == len(inputs)
            assert all(isinstance(emb, list) for emb in response.embeddings)
            assert response.total_tokens > 0

    def test_semantic_similarity(self):
        """Test embedding semantic similarity characteristics."""
        with self.vcr.use_cassette("semantic_similarity.yaml"):
            inputs = [
                "The quick brown fox jumps over the lazy dog.",
                "A fast auburn fox leaps above the sleepy canine.",  # Similar
                "Python is a programming language.",  # Different
            ]

            response = self.provider.embed(inputs=inputs, model_id=self.model_id)
            embeddings = np.array(response.embeddings)

            # Calculate cosine similarity
            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            sim_similar = cosine_similarity(embeddings[0], embeddings[1])
            sim_different = cosine_similarity(embeddings[0], embeddings[2])

            assert (
                sim_similar > sim_different
            ), "Similar sentences should have higher similarity"
            assert 0 <= sim_similar <= 1, "Similarity should be between 0 and 1"

    def test_error_handling(self):
        """Test comprehensive error handling scenarios."""
        with self.vcr.use_cassette("error_handling.yaml"):
            # Invalid input type
            with pytest.raises(ValueError):
                self.provider.embed(inputs=[123], model_id=self.model_id)

            # Empty input
            with pytest.raises(ValueError):
                self.provider.embed(inputs=[], model_id=self.model_id)

            # Invalid model ID
            with pytest.raises((InvalidRequestError, AuthenticationError)):
                self.provider.embed(inputs=["test"], model_id="invalid-model-id")

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling scenarios."""
        with self.vcr.use_cassette("async_error_handling.yaml"):
            # Invalid input type
            with pytest.raises(ValueError):
                await self.provider.async_embed(inputs=[123], model_id=self.model_id)

            # Empty input
            with pytest.raises(ValueError):
                await self.provider.async_embed(inputs=[], model_id=self.model_id)

            # Invalid model ID
            with pytest.raises((InvalidRequestError, AuthenticationError)):
                await self.provider.async_embed(
                    inputs=["test"], model_id="invalid-model-id"
                )

    def test_rate_limit_handling(self):
        """Test rate limit handling and backoff."""
        with self.vcr.use_cassette("rate_limit_handling.yaml"):
            # Configure provider with strict rate limits for testing
            self.provider.rate_limit_config = RateLimitConfig(
                requests_per_minute=2,
                tokens_per_minute=100,
                max_retries=2,
                initial_retry_delay=0.1,
                max_retry_delay=0.3,
                jitter_factor=0.1,
            )

            # Make rapid requests to trigger rate limit
            with pytest.raises(RateLimitError):
                for _ in range(5):
                    self.provider.embed(
                        inputs=["test" * 100],  # Large input to consume tokens
                        model_id=self.model_id,
                    )
