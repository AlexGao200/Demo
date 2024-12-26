from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any, Union, Tuple
from project_types.provider_limiter import ProviderLimiter, RateLimitConfig
from loguru import logger
import base64
from io import BytesIO
from PIL import Image
from project_types.error_types import (
    RateLimitError,
    TimeoutError,
    ProviderError,
    AuthenticationError,
    InvalidRequestError,
    ConnectionError,
)


# Type aliases for clarity
ImageInput = Union[Image.Image, str]  # PIL Image or base64 string
TextInput = str
MultimodalInput = Union[TextInput, ImageInput, Tuple[TextInput, ImageInput]]
InputType = Union[MultimodalInput, List[MultimodalInput]]


@dataclass
class EmbeddingResponse:
    """Standardized response across embedding providers"""

    embeddings: List[List[float]]
    total_tokens: int
    model_id: str
    input_type: Optional[str] = None  # e.g., 'text', 'image', 'multimodal'
    raw_response: Any = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    def __init__(
        self,
        sync_client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """Initialize the provider with optional clients and rate limiting"""
        self.sync_client = sync_client
        self.async_client = async_client
        self.rate_limit_config = rate_limit_config or RateLimitConfig(
            requests_per_minute=60,  # Conservative default
            tokens_per_minute=150000,  # Conservative default
            max_retries=8,
            initial_retry_delay=1.0,
            max_retry_delay=64.0,
            jitter_factor=0.1,
        )

    def _prepare_inputs(self, inputs: InputType) -> List[MultimodalInput]:
        """Standardize inputs to list format"""
        if not isinstance(inputs, list):
            return [inputs]
        return inputs

    def _process_image(self, image: ImageInput) -> str:
        """Convert image to base64 string if needed"""

        if isinstance(image, str) and (
            image.startswith("http://") or image.startswith("https://")
        ):
            # Download image from URL
            import requests

            response = requests.get(image)
            image = Image.open(BytesIO(response.content))

        if isinstance(image, Image.Image):
            # Convert PIL Image to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"

        if isinstance(image, str):
            # Assume it's already base64 encoded
            return f"data:image/png;base64,{image}"

        raise ValueError(f"Unsupported image type: {type(image)}")

    def _count_tokens(self, inputs: List[MultimodalInput]) -> int:
        """Estimate token count for rate limiting"""
        total_tokens = 0
        for input_item in inputs:
            if isinstance(input_item, tuple):
                # Text + Image pair
                text, _ = input_item
                total_tokens += len(text) // 4 + 1 + 1024  # Rough image token estimate
            elif isinstance(input_item, (Image.Image, str)):
                if isinstance(input_item, str) and not (
                    input_item.startswith("data:")
                    or input_item.startswith("http://")
                    or input_item.startswith("https://")
                ):
                    # Text only
                    total_tokens += len(input_item) // 4 + 1
                else:
                    # Image only
                    total_tokens += 1024 * 1024 / 600  # Rough image token estimate
            else:
                raise ValueError(f"Unsupported input type: {type(input_item)}")
        return total_tokens

    async def _handle_rate_limits(self, token_count: int):
        """Check rate limits using token bucket algorithm"""
        await ProviderLimiter._acquire(
            self.provider_type, self.rate_limit_config, token_count
        )

    def _handle_rate_limits_sync(self, token_count: int):
        """Synchronous version of rate limit checking"""
        ProviderLimiter._acquire_sync(
            self.provider_type, self.rate_limit_config, token_count
        )

    async def _handle_api_error(self, e: Exception, operation: str):
        """Centralized error handling with proper logging and classification"""
        error_msg = str(e).lower()
        logger.error(f"{operation} failed: {type(e).__name__} - {error_msg}")

        if any(
            x in error_msg for x in ["rate", "too many requests", "429", "Overloaded"]
        ):
            logger.warning("Rate limit reached, implementing backoff")
            await ProviderLimiter.handle_429(self.provider_type, self.rate_limit_config)
            raise RateLimitError(f"Rate limit exceeded: {error_msg}")
        elif "timeout" in error_msg:
            raise TimeoutError(f"Request timeout: {error_msg}")
        elif any(x in error_msg for x in ["connection", "network", "socket"]):
            raise ConnectionError(f"Connection error: {error_msg}")
        elif any(x in error_msg for x in ["auth", "key", "permission"]):
            raise AuthenticationError(f"Authentication error: {error_msg}")
        elif any(x in error_msg for x in ["invalid", "malformed", "bad request"]):
            raise InvalidRequestError(f"Invalid request: {error_msg}")
        else:
            raise ProviderError(f"Provider error: {error_msg}")

    def _handle_api_error_sync(self, e: Exception, operation: str):
        """Synchronous version of error handling"""
        error_msg = str(e).lower()
        logger.error(f"{operation} failed: {type(e).__name__} - {error_msg}")

        if any(
            x in error_msg
            for x in ["rate", "too many requests", "429", "admitted", "Overloaded"]
        ):
            logger.warning("Rate limit reached, implementing backoff")
            ProviderLimiter.handle_429_sync(self.provider_type, self.rate_limit_config)
            raise RateLimitError(f"Rate limit exceeded: {error_msg}")
        elif "timeout" in error_msg:
            raise TimeoutError(f"Request timeout: {error_msg}")
        elif any(x in error_msg for x in ["connection", "network", "socket"]):
            raise ConnectionError(f"Connection error: {error_msg}")
        elif any(x in error_msg for x in ["auth", "key", "permission"]):
            raise AuthenticationError(f"Authentication error: {error_msg}")
        elif any(x in error_msg for x in ["invalid", "malformed", "bad request"]):
            raise InvalidRequestError(f"Invalid request: {error_msg}")
        else:
            raise ProviderError(f"Provider error: {error_msg}")

    @abstractmethod
    def embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings synchronously"""
        pass

    @abstractmethod
    async def async_embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings asynchronously"""
        pass
