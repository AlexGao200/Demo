from typing import Optional, Union
import voyageai
from PIL import Image
from project_types.embedding_provider import (
    EmbeddingProvider,
    EmbeddingResponse,
    InputType,
    MultimodalInput,
)
from project_types.provider_limiter import RateLimitConfig
from loguru import logger
import base64
from io import BytesIO


class VoyageProvider(EmbeddingProvider):
    """Voyage AI implementation supporting both sync and async operations"""

    def __init__(
        self,
        sync_client: Optional[voyageai.Client] = None,
        async_client: Optional[voyageai.AsyncClient] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        super().__init__(
            sync_client,
            async_client,
            rate_limit_config
            or RateLimitConfig(
                requests_per_minute=1800,  # Adjust based on your tier
                tokens_per_minute=1.8 * 10 * 8,  # Adjust based on your tier
                max_retries=8,
                initial_retry_delay=1.0,
                max_retry_delay=64.0,
                jitter_factor=0.1,
            ),
        )
        self.provider_type = "voyage"

    def _prepare_voyage_inputs(
        self, inputs: list[MultimodalInput]
    ) -> list[Union[str, list[Union[str, Image.Image]]]]:
        """Convert inputs to Voyage's expected format"""
        if not inputs:
            raise ValueError("Empty input provided")

        voyage_inputs = []
        for input_item in inputs:
            if isinstance(input_item, tuple):
                # Text + Image pair
                text, image = input_item
                if isinstance(image, str):
                    # Convert base64/URL to PIL Image
                    image = Image.open(
                        BytesIO(
                            base64.b64decode(
                                image.split(",")[1] if "," in image else image
                            )
                        )
                    )
                voyage_inputs.append([text, image])
            elif isinstance(input_item, (Image.Image, str)):
                if isinstance(input_item, str) and not (
                    input_item.startswith("data:")
                    or input_item.startswith("http://")
                    or input_item.startswith("https://")
                ):
                    # Text only
                    voyage_inputs.append([input_item])
                else:
                    # Image only
                    if isinstance(input_item, str):
                        # Convert base64/URL to PIL Image
                        image = Image.open(
                            BytesIO(
                                base64.b64decode(
                                    input_item.split(",")[1]
                                    if "," in input_item
                                    else input_item
                                )
                            )
                        )
                        voyage_inputs.append([image])
                    else:
                        voyage_inputs.append([input_item])
            else:
                raise ValueError(f"Unsupported input type: {type(input_item)}")
        return voyage_inputs

    def embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings synchronously using Voyage AI"""
        if self.sync_client is None:
            raise NotImplementedError(
                "Sync client not provided. Use async_embed instead."
            )

        if not inputs:
            raise ValueError("Empty input provided")

        try:
            inputs = self._prepare_inputs(inputs)
            token_count = self._count_tokens(inputs)
            self._handle_rate_limits_sync(token_count)

            # Convert inputs to Voyage's format
            voyage_inputs = self._prepare_voyage_inputs(inputs)

            # Log request metrics
            logger.debug(
                f"Making sync request to Voyage AI {model_id} with {len(inputs)} inputs"
            )

            # Use multimodal_embed for all cases as it handles both text and images
            response = self.sync_client.multimodal_embed(
                inputs=voyage_inputs,
                model=model_id,
            )

            # Determine input type based on inputs
            detected_type = (
                "multimodal"
                if any(isinstance(i, tuple) for i in inputs)
                else "image"
                if all(
                    isinstance(i, (Image.Image, str))
                    and (
                        isinstance(i, Image.Image)
                        or i.startswith("data:")
                        or i.startswith("http://")
                        or i.startswith("https://")
                    )
                    for i in inputs
                )
                else "text"
            )

            return EmbeddingResponse(
                embeddings=response.embeddings,
                total_tokens=token_count,
                model_id=model_id,
                input_type=detected_type,
                raw_response=response,
            )

        except Exception as e:
            self._handle_api_error_sync(e, "Voyage embedding generation")

    async def async_embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings asynchronously using Voyage AI"""
        if self.async_client is None:
            raise NotImplementedError("Async client not provided. Use embed instead.")

        if not inputs:
            raise ValueError("Empty input provided")

        try:
            inputs = self._prepare_inputs(inputs)
            token_count = self._count_tokens(inputs)
            await self._handle_rate_limits(token_count)

            # Convert inputs to Voyage's format
            voyage_inputs = self._prepare_voyage_inputs(inputs)

            # Log request metrics
            logger.debug(
                f"Making async request to Voyage AI {model_id} with {len(inputs)} inputs"
            )

            # Use multimodal_embed for all cases as it handles both text and images
            response = await self.async_client.multimodal_embed(
                inputs=voyage_inputs,
                model=model_id,
            )

            # Determine input type based on inputs
            detected_type = (
                "multimodal"
                if any(isinstance(i, tuple) for i in inputs)
                else "image"
                if all(
                    isinstance(i, (Image.Image, str))
                    and (
                        isinstance(i, Image.Image)
                        or i.startswith("data:")
                        or i.startswith("http://")
                        or i.startswith("https://")
                    )
                    for i in inputs
                )
                else "text"
            )

            return EmbeddingResponse(
                embeddings=response.embeddings,
                total_tokens=token_count,
                model_id=model_id,
                input_type=detected_type,
                raw_response=response,
            )

        except Exception as e:
            await self._handle_api_error(e, "Voyage embedding generation")
