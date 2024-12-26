from typing import Dict, List, Optional, Any, AsyncIterator, Iterator, Union
from project_types.llm_provider import (
    LLMProvider,
    ProviderResponse,
    RateLimitConfig,
    ProviderError,
    AuthenticationError,
    InvalidRequestError,
    ConnectionError,
    Message,
)
from loguru import logger


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs supporting both sync and async operations"""

    def __init__(
        self,
        sync_client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(
            rate_limit_config
            or RateLimitConfig(
                requests_per_minute=550,  # Per website, 600 for pro (base tier is 60)
                tokens_per_minute=90000,
                max_retries=8,
                initial_retry_delay=2.0,  # OpenAI recommends starting with 2s
                max_retry_delay=64.0,
                jitter_factor=0.5,
            ),
            provider_type="openai",
        )
        self.sync_client = sync_client
        self.async_client = async_client
        if base_url:
            if sync_client:
                self.sync_client.base_url = base_url
            if async_client:
                self.async_client.base_url = base_url

    def _prepare_args(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Prepare arguments for OpenAI's Chat Completions API"""
        args = self._prepare_base_args(**kwargs)

        # Convert messages to OpenAI format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg["content"], str):
                formatted_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )
            else:
                # For system messages with content blocks, concatenate text content
                # Note: OpenAI doesn't support cache control, so we just concatenate the text
                content_text = " ".join(
                    block["text"] for block in msg["content"] if block["type"] == "text"
                )
                formatted_messages.append(
                    {"role": msg["role"], "content": content_text}
                )

        args["messages"] = formatted_messages

        # Map parameters to OpenAI equivalents (most are already compatible)
        if "temperature" in args:
            args["temperature"] = min(max(args["temperature"], 0), 2)
        if "max_tokens" in args and args["max_tokens"] is not None:
            pass
        else:
            args["max_tokens"] = 1000
        if "top_p" in args:
            args["top_p"] = min(max(args["top_p"], 0), 1)

        return args

    def generate(
        self, messages: List[Message], model_id: str, **kwargs
    ) -> Union[ProviderResponse, Iterator[str]]:
        """Synchronous generation with improved error handling and monitoring"""
        if self.sync_client is None:
            raise NotImplementedError(
                "Sync client not provided. Use agenerate instead."
            )

        try:
            # Use centralized token counting
            token_count = self._count_tokens(messages)
            self.check_rate_limits_sync(tokens=token_count)

            args = self._prepare_args(messages=messages, model=model_id, **kwargs)

            # Log request metrics
            logger.debug(f"Making request to {model_id} with {token_count} tokens")

            response = self.sync_client.chat.completions.create(**args)

            if kwargs.get("stream", False):
                return self._generate_stream_base(response)

            if hasattr(response, "usage"):
                output_tokens = response.usage.completion_tokens
                self._track_completion_tokens(output_tokens)

                # Update token tracking
                self._token_count += response.usage.total_tokens
                self._input_token_count += response.usage.prompt_tokens
                self._output_token_count += response.usage.completion_tokens

                # Log usage metrics
                logger.debug(
                    f"Request completed. Input tokens: {response.usage.prompt_tokens}, "
                    f"Output tokens: {response.usage.completion_tokens}"
                )

            return ProviderResponse(
                content=response.choices[0].message.content,
                total_tokens=response.usage.total_tokens
                if hasattr(response, "usage")
                else token_count,  # Use counted tokens as fallback
                input_tokens=response.usage.prompt_tokens
                if hasattr(response, "usage")
                else token_count,
                output_tokens=response.usage.completion_tokens
                if hasattr(response, "usage")
                else 0,
                raw_response=response,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "internal server error" in error_msg or "500" in error_msg:
                raise ProviderError(f"Internal server error: {error_msg}")
            elif "unauthorized" in error_msg or "authentication" in error_msg:
                raise AuthenticationError(f"Authentication failed: {error_msg}")
            elif "invalid" in error_msg or "bad request" in error_msg:
                raise InvalidRequestError(f"Invalid request: {error_msg}")
            elif "connection" in error_msg or "network" in error_msg:
                raise ConnectionError(f"Connection error: {error_msg}")
            else:
                raise ProviderError(f"Provider error: {error_msg}")

    async def agenerate(
        self, messages: List[Message], model_id: str, **kwargs
    ) -> Union[ProviderResponse, AsyncIterator[str]]:
        """Asynchronous generation with improved error handling and monitoring"""
        if self.async_client is None:
            raise NotImplementedError(
                "Async client not provided. Use generate instead."
            )

        try:
            # Use centralized token counting
            token_count = self._count_tokens(messages)
            await self.check_rate_limits(tokens=token_count)

            args = self._prepare_args(messages=messages, model=model_id, **kwargs)

            # Log request metrics
            logger.debug(
                f"Making async request to {model_id} with {token_count} tokens"
            )

            response = await self.async_client.chat.completions.create(**args)

            if kwargs.get("stream", False):
                return self._agenerate_stream_base(response)

            if hasattr(response, "usage"):
                output_tokens = response.usage.completion_tokens
                await self._atrack_completion_tokens(output_tokens)

                # Update token tracking
                self._token_count += response.usage.total_tokens
                self._input_token_count += response.usage.prompt_tokens
                self._output_token_count += response.usage.completion_tokens

                # Log usage metrics
                logger.debug(
                    f"Async request completed. Input tokens: {response.usage.prompt_tokens}, "
                    f"Output tokens: {response.usage.completion_tokens}"
                )

            return ProviderResponse(
                content=response.choices[0].message.content,
                total_tokens=response.usage.total_tokens
                if hasattr(response, "usage")
                else token_count,  # Use counted tokens as fallback
                input_tokens=response.usage.prompt_tokens
                if hasattr(response, "usage")
                else token_count,
                output_tokens=response.usage.completion_tokens
                if hasattr(response, "usage")
                else 0,
                raw_response=response,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "internal server error" in error_msg or "500" in error_msg:
                raise ProviderError(f"Internal server error: {error_msg}")
            elif "unauthorized" in error_msg or "authentication" in error_msg:
                raise AuthenticationError(f"Authentication failed: {error_msg}")
            elif "invalid" in error_msg or "bad request" in error_msg:
                raise InvalidRequestError(f"Invalid request: {error_msg}")
            elif "connection" in error_msg or "network" in error_msg:
                raise ConnectionError(f"Connection error: {error_msg}")
            else:
                raise ProviderError(f"Provider error: {error_msg}")
