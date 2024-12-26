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
from anthropic import Anthropic, AsyncAnthropic


class AnthropicProvider(LLMProvider):
    """Anthropic implementation supporting both sync and async operations"""

    def __init__(
        self,
        sync_client: Optional[Anthropic] = None,
        async_client: Optional[AsyncAnthropic] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        super().__init__(
            rate_limit_config
            or RateLimitConfig(
                requests_per_minute=1800,
                tokens_per_minute=50000,
                max_retries=8,
                initial_retry_delay=1.0,
                max_retry_delay=64.0,
                jitter_factor=0.1,
            ),
            provider_type="anthropic",
        )
        self.sync_client = sync_client
        self.async_client = async_client

    def _prepare_args(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Prepare arguments for Anthropic's Messages API"""
        args = self._prepare_base_args(**kwargs)

        # Remove stream parameter as it's handled by method choice
        args.pop("stream", None)

        # Convert messages to Anthropic format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg["content"], str):
                formatted_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )
            else:
                # Handle structured content
                if msg["role"] == "system":
                    # For system messages, preserve block structure with cache control
                    system_blocks = []
                    for block in msg["content"]:
                        system_block = {"type": block["type"], "text": block["text"]}
                        if "cache_control" in block:
                            system_block["cache_control"] = block["cache_control"]
                        system_blocks.append(system_block)
                    args["system"] = system_blocks
                else:
                    # For non-system messages, concatenate text content
                    content_text = " ".join(
                        block["text"]
                        for block in msg["content"]
                        if block["type"] == "text"
                    )
                    formatted_messages.append(
                        {"role": msg["role"], "content": content_text}
                    )

        args["messages"] = formatted_messages

        # Map OpenAI parameters to Anthropic equivalents
        if "temperature" in args:
            args["temperature"] = min(max(args["temperature"], 0), 1)
        if "max_tokens" in args and args["max_tokens"] is not None:
            pass
        else:
            args["max_tokens"] = 1000
        if "stop" in args:
            args["stop_sequences"] = args.pop("stop")
        if "top_p" in args:
            args["top_p"] = min(max(args["top_p"], 0), 1)

        return args

    def _generate_stream(self, stream: Any) -> Iterator[str]:
        """Handle streaming response using Messages API format"""
        try:
            for event in stream:
                if event.type == "content_block_delta":
                    yield event.delta.text
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
        finally:
            if hasattr(stream, "close"):
                stream.close()

    async def _agenerate_stream(self, stream: Any) -> AsyncIterator[str]:
        """Handle streaming response asynchronously using Messages API format"""
        try:
            async for event in stream:
                if event.type == "content_block_delta":
                    yield event.delta.text
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
        finally:
            if hasattr(stream, "close"):
                await stream.close()

    def generate(
        self, messages: List[Message], model_id: str, **kwargs
    ) -> Union[ProviderResponse, Iterator[str]]:
        """Synchronous generation using Messages API"""
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

            if kwargs.get("stream", False):
                # For streaming, use create with stream=True
                stream = self.sync_client.messages.create(stream=True, **args)
                return self._generate_stream(stream)

            # For non-streaming, use create()
            response = self.sync_client.messages.create(**args)

            if hasattr(response, "usage"):
                output_tokens = response.usage.output_tokens
                self._track_completion_tokens(output_tokens)

                # Update token tracking
                self._token_count += (
                    response.usage.input_tokens + response.usage.output_tokens
                )
                self._input_token_count += response.usage.input_tokens
                self._output_token_count += response.usage.output_tokens

                # Log usage metrics
                logger.debug(
                    f"Request completed. Input tokens: {response.usage.input_tokens}, "
                    f"Output tokens: {response.usage.output_tokens}"
                )

            return ProviderResponse(
                content=response.content[0].text,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
                if hasattr(response, "usage")
                else token_count,  # Use counted tokens as fallback
                input_tokens=response.usage.input_tokens
                if hasattr(response, "usage")
                else token_count,
                output_tokens=response.usage.output_tokens
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
        """Asynchronous generation using Messages API"""
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

            if kwargs.get("stream", False):
                # For streaming, use create with stream=True
                stream = await self.async_client.messages.create(stream=True, **args)
                return self._agenerate_stream(stream)

            # For non-streaming, use create()
            response = await self.async_client.messages.create(**args)

            if hasattr(response, "usage"):
                output_tokens = response.usage.output_tokens
                await self._atrack_completion_tokens(output_tokens)

                # Update token tracking
                self._token_count += (
                    response.usage.input_tokens + response.usage.output_tokens
                )
                self._input_token_count += response.usage.input_tokens
                self._output_token_count += response.usage.output_tokens

                # Log usage metrics
                logger.debug(
                    f"Async request completed. Input tokens: {response.usage.input_tokens}, "
                    f"Output tokens: {response.usage.output_tokens}"
                )

            return ProviderResponse(
                content=response.content[0].text,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
                if hasattr(response, "usage")
                else token_count,  # Use counted tokens as fallback
                input_tokens=response.usage.input_tokens
                if hasattr(response, "usage")
                else token_count,
                output_tokens=response.usage.output_tokens
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
