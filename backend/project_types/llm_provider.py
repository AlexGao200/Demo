from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, AsyncIterator, Iterator, Union, TypedDict
from utils.types import NOT_GIVEN, NotGiven
import random
import asyncio
from loguru import logger
import tiktoken
import functools
import time
import base64
from project_types.error_types import (
    RateLimitError,
    TimeoutError,
    ProviderError,
    ConnectionError,
    AuthenticationError,
    InvalidRequestError,
)
from project_types.provider_limiter import ProviderLimiter, RateLimitConfig


class CacheControl(TypedDict, total=False):
    """Cache control settings for message content"""

    type: str  # e.g., "ephemeral" for temporary content


class MessageContent(TypedDict):
    """Content block for a message"""

    type: str  # "text" or "image"
    text: str  # For text content
    image_url: Optional[str]  # For image content
    cache_control: Optional[CacheControl]  # Optional cache control settings


class Message(TypedDict):
    """Standardized message format across providers"""

    role: str  # "system", "user", "assistant"
    content: Union[str, List[MessageContent]]  # Either raw text or structured content


@dataclass
class ProviderResponse:
    """Standardized response across providers"""

    content: str
    total_tokens: int
    input_tokens: int = 0  # Track input tokens for billing
    output_tokens: int = 0  # Track output tokens for billing
    raw_response: Any = None


def retry_with_exponential_backoff(func):
    """Decorator to add retry logic with exponential backoff"""

    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        max_retries = self.rate_limit_config.max_retries
        initial_delay = self.rate_limit_config.initial_retry_delay
        max_delay = self.rate_limit_config.max_retry_delay
        jitter_factor = self.rate_limit_config.jitter_factor

        for attempt in range(max_retries + 1):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                # Don't retry on certain errors
                if isinstance(e, (AuthenticationError, InvalidRequestError)):
                    raise

                if attempt == max_retries:
                    raise

                # Calculate delay with jitter
                delay = min(initial_delay * (2**attempt), max_delay)
                jitter = delay * jitter_factor
                delay += random.uniform(-jitter, jitter)

                logger.warning(
                    f"Request failed with {type(e).__name__}: {str(e)}. "
                    f"Retrying ({attempt + 1}/{max_retries}) after {delay:.2f}s"
                )
                await asyncio.sleep(delay)

    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        max_retries = self.rate_limit_config.max_retries
        initial_delay = self.rate_limit_config.initial_retry_delay
        max_delay = self.rate_limit_config.max_retry_delay
        jitter_factor = self.rate_limit_config.jitter_factor

        for attempt in range(max_retries + 1):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Don't retry on certain errors
                if isinstance(e, (AuthenticationError, InvalidRequestError)):
                    raise

                if attempt == max_retries:
                    raise

                # Calculate delay with jitter
                delay = min(initial_delay * (2**attempt), max_delay)
                jitter = delay * jitter_factor
                delay += random.uniform(-jitter, jitter)

                logger.warning(
                    f"Request failed with {type(e).__name__}: {str(e)}. "
                    f"Retrying ({attempt + 1}/{max_retries}) after {delay:.2f}s"
                )
                time.sleep(delay)

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, rate_limit_config: RateLimitConfig, provider_type: str):
        self.rate_limit_config = rate_limit_config
        self.provider_type = provider_type
        self._token_count = 0
        self._input_token_count = 0  # For billing tracking
        self._output_token_count = 0  # For billing tracking
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Shared tokenizer
        # Initialize system message cache
        self._system_message_cache: Dict[str, Any] = {}

    def _extract_image_dimensions(self, base64_data: str) -> tuple[int, int]:
        """Extract image dimensions from base64 data"""
        try:
            # Decode base64 header to get image info
            header = base64.b64decode(
                base64_data.split(",")[1] if "," in base64_data else base64_data
            )[:24]

            # Check for JPEG/PNG markers
            if header.startswith(b"\xff\xd8"):  # JPEG
                # Find SOFn markers
                for i in range(2, len(header) - 8):
                    if header[i] == 0xFF and 0xC0 <= header[i + 1] <= 0xCF:
                        height = int.from_bytes(header[i + 5 : i + 7], "big")
                        width = int.from_bytes(header[i + 7 : i + 9], "big")
                        return width, height
            elif header.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                return width, height

            # Default conservative estimate if dimensions can't be extracted
            return 1024, 1024  # Conservative default
        except Exception as e:
            logger.warning(f"Failed to extract image dimensions: {e}")
            return 1568, 1568  # Conservative default

    def _calculate_image_tokens(self, image_data: Union[str, Dict]) -> int:
        """Calculate token usage for an image using width * height / 600 formula"""
        try:
            # Handle different image formats from different providers
            if isinstance(image_data, dict):
                if "source" in image_data:  # Anthropic format
                    base64_data = image_data["source"]["data"]
                elif "image_url" in image_data:  # OpenAI format
                    url = image_data["image_url"]
                    if url.startswith("data:image"):
                        base64_data = url.split(",")[1]
                    else:
                        logger.warning(
                            "Non-base64 image URL found, using conservative estimate"
                        )
                        return int((1568 * 1568) / 600)  # Conservative estimate
            else:
                base64_data = image_data

            width, height = self._extract_image_dimensions(base64_data)
            tokens = int((width * height) / 600)
            logger.debug(
                f"Image dimensions: {width}x{height}, calculated tokens: {tokens}"
            )
            return tokens
        except Exception as e:
            logger.warning(f"Error calculating image tokens: {e}")
            return int((1568 * 1568) / 600)  # Conservative fallback

    def _count_tokens(self, messages: List[Message]) -> int:
        """
        Centralized token counting using tiktoken.
        Returns total token count for the messages, including images.
        """
        try:
            total_tokens = 0
            for message in messages:
                # Handle content that could be either string or list of content blocks
                if isinstance(message.get("content"), str):
                    content_tokens = len(self.tokenizer.encode(message["content"]))
                    format_tokens = 4  # Basic message overhead
                    total_tokens += content_tokens + format_tokens
                elif isinstance(message.get("content"), list):
                    for content_block in message["content"]:
                        if content_block["type"] == "text":
                            content_tokens = len(
                                self.tokenizer.encode(content_block["text"])
                            )
                            format_tokens = 4  # Basic message overhead
                            total_tokens += content_tokens + format_tokens
                        elif content_block["type"] == "image":
                            # Add image token calculation
                            image_tokens = self._calculate_image_tokens(
                                content_block.get("image_url") or content_block
                            )
                            total_tokens += image_tokens
                            logger.debug(f"Added {image_tokens} tokens for image")

            return total_tokens
        except Exception as e:
            logger.error(f"Token counting error: {str(e)}")
            # Fallback to conservative estimation
            return sum(len(str(msg.get("content", "")).split()) * 3 for msg in messages)

    def _prepare_base_args(self, **kwargs) -> Dict[str, Any]:
        """Shared argument preparation logic"""
        args = {k: v for k, v in kwargs.items() if not isinstance(v, NotGiven)}
        if args.get("max_tokens") is None:
            args.pop("max_tokens", None)
        return args

    def _prepare_messages(self, messages: List[Message]) -> List[Message]:
        """
        Prepare messages for provider-specific formatting.
        Override in provider classes for specific message handling.
        """
        return messages

    def _generate_stream_base(self, response: Any) -> Iterator[str]:
        """Base streaming response handler"""
        try:
            for chunk in response:
                if hasattr(chunk.choices[0], "delta"):
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                elif hasattr(chunk.choices[0], "text"):
                    if chunk.choices[0].text is not None:
                        yield chunk.choices[0].text
        except Exception as e:
            self._handle_api_error_sync(e, "Stream generation")

    async def _agenerate_stream_base(self, response: Any) -> AsyncIterator[str]:
        """Base async streaming response handler"""
        try:
            async for chunk in response:
                if hasattr(chunk.choices[0], "delta"):
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                elif hasattr(chunk.choices[0], "text"):
                    if chunk.choices[0].text is not None:
                        yield chunk.choices[0].text
        except Exception as e:
            await self._handle_api_error(e, "Async stream generation")

    async def _handle_api_error(self, e: Exception, operation: str):
        """Centralized error handling with proper logging and classification"""
        error_type = type(e).__name__
        error_msg = str(e).lower()

        logger.error(f"{operation} failed: {error_type} - {error_msg}")

        if any(
            x in error_msg for x in ["rate", "too many requests", "429", "Overloaded"]
        ):
            logger.warning("Rate limit reached, implementing backoff")
            await self._handle_rate_limit()
            raise RateLimitError(f"Rate limit exceeded: {error_msg}")
        elif "timeout" in error_msg:
            logger.warning("Request timeout, retry recommended")
            raise TimeoutError(f"Request timeout: {error_msg}")
        elif any(x in error_msg for x in ["connection", "network", "socket"]):
            raise ConnectionError(f"Connection error: {error_msg}")
        elif any(x in error_msg for x in ["auth", "key", "permission"]):
            raise AuthenticationError(f"Authentication error: {error_msg}")
        elif any(x in error_msg for x in ["invalid", "malformed", "bad request"]):
            raise InvalidRequestError(f"Invalid request: {error_msg}")
        else:
            logger.error(f"Unexpected error in {operation}: {error_msg}")
            raise ProviderError(f"Provider error: {error_msg}")

    def _handle_api_error_sync(self, e: Exception, operation: str):
        """Centralized error handling with proper logging and classification"""
        error_type = type(e).__name__
        error_msg = str(e).lower()

        logger.error(f"{operation} failed: {error_type} - {error_msg}")

        if any(
            x in error_msg for x in ["rate", "too many requests", "429", "Overloaded"]
        ):
            logger.warning("Rate limit reached, implementing backoff")
            self._handle_rate_limit_sync()
            raise RateLimitError(f"Rate limit exceeded: {error_msg}")
        elif "timeout" in error_msg:
            logger.warning("Request timeout, retry recommended")
            raise TimeoutError(f"Request timeout: {error_msg}")
        elif any(x in error_msg for x in ["connection", "network", "socket"]):
            raise ConnectionError(f"Connection error: {error_msg}")
        elif any(x in error_msg for x in ["auth", "key", "permission"]):
            raise AuthenticationError(f"Authentication error: {error_msg}")
        elif any(x in error_msg for x in ["invalid", "malformed", "bad request"]):
            raise InvalidRequestError(f"Invalid request: {error_msg}")
        else:
            logger.error(f"Unexpected error in {operation}: {error_msg}")
            raise ProviderError(f"Provider error: {error_msg}")

    async def check_rate_limits(self, tokens: int = 0) -> None:
        """Check rate limits using token bucket algorithm"""
        await ProviderLimiter._acquire(
            self.provider_type, self.rate_limit_config, tokens
        )

    def check_rate_limits_sync(self, tokens: int = 0) -> None:
        """Synchronous version of rate limit checking"""
        ProviderLimiter._acquire_sync(
            self.provider_type, self.rate_limit_config, tokens
        )

    async def _handle_rate_limit(self):
        """Handle 429 response asynchronously"""
        await ProviderLimiter.handle_429(self.provider_type, self.rate_limit_config)

    def _track_completion_tokens(self, output_tokens: int):
        """Track completion tokens after response synchronously"""
        _, _, token_tracker = ProviderLimiter.get_limiters(
            self.provider_type, self.rate_limit_config
        )
        token_tracker.add_usage_sync(0, output_tokens)

    async def _atrack_completion_tokens(self, output_tokens: int):
        """Track completion tokens after response asynchronously"""
        _, _, token_tracker = ProviderLimiter.get_limiters(
            self.provider_type, self.rate_limit_config
        )
        await token_tracker.add_usage(0, output_tokens)

    @abstractmethod
    @retry_with_exponential_backoff
    def generate(
        self,
        messages: List[Message],
        model_id: str,
        stream: bool = False,
        max_tokens: Optional[int] = None,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: Any | NotGiven = NOT_GIVEN,
        functions: List[Any] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        response_format: Any | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str]] | NotGiven = NOT_GIVEN,
        system_prompts: Union[Optional[str], List[str]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Any | NotGiven = NOT_GIVEN,
        tools: List[Any] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        **kwargs,
    ) -> Union[ProviderResponse, Iterator[str]]:
        """Generate a response synchronously"""
        pass

    @abstractmethod
    @retry_with_exponential_backoff
    async def agenerate(
        self,
        messages: List[Message],
        model_id: str,
        stream: bool = False,
        max_tokens: Optional[int] = None,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: Any | NotGiven = NOT_GIVEN,
        functions: List[Any] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        response_format: Any | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str]] | NotGiven = NOT_GIVEN,
        system_prompts: Union[Optional[str], List[str]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Any | NotGiven = NOT_GIVEN,
        tools: List[Any] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        **kwargs,
    ) -> Union[ProviderResponse, AsyncIterator[str]]:
        """Generate a response asynchronously"""
        pass

    def _handle_rate_limit_sync(self):
        """Handle 429 response synchronously"""
        ProviderLimiter.handle_429_sync(self.provider_type, self.rate_limit_config)
