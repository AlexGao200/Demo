from typing import Optional
import cohere
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


class CohereProvider(EmbeddingProvider):
    """Cohere implementation supporting both sync and async operations"""

    def __init__(
        self,
        sync_client: Optional[cohere.ClientV2] = None,
        async_client: Optional[cohere.AsyncClientV2] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        super().__init__(
            sync_client,
            async_client,
            rate_limit_config
            or RateLimitConfig(
                requests_per_minute=1000,  # Adjust based on your tier
                tokens_per_minute=1.5 * 10**8,  # Adjust based on your tier
                max_retries=8,
                initial_retry_delay=1.0,
                max_retry_delay=64.0,
                jitter_factor=0.1,
            ),
        )
        self.provider_type = "cohere"

    def _validate_inputs(self, inputs: InputType) -> None:
        """Validate inputs before processing"""
        if not inputs:
            raise ValueError("Empty input provided")

        if not all(
            isinstance(input_item, (str, tuple, list, Image.Image))
            for input_item in inputs
        ):
            raise ValueError("Not all inputs are string, tuple, list, or image")

    def _prepare_cohere_inputs(
        self, inputs: list[MultimodalInput], input_type: Optional[str]
    ) -> tuple[list[str], list[str]]:
        """Convert inputs to Cohere's expected format, separating texts and images"""
        texts = []
        images = []

        for input_item in inputs:
            if isinstance(input_item, tuple):
                # Text + Image pair
                text, image = input_item
                texts.append(text)
                if isinstance(image, str):
                    images.append(
                        image
                        if image.startswith("data:")
                        else f"data:image/png;base64,{image}"
                    )
                else:
                    # Convert PIL Image to base64
                    buffered = BytesIO()
                    image.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    images.append(f"data:image/png;base64,{img_str}")
            elif isinstance(input_item, (Image.Image, str)):
                if isinstance(input_item, str) and not (
                    input_item.startswith("data:")
                    or input_item.startswith("http://")
                    or input_item.startswith("https://")
                ):
                    # Text only
                    texts.append(input_item)
                else:
                    # Image only
                    if isinstance(input_item, str):
                        images.append(
                            input_item
                            if input_item.startswith("data:")
                            else f"data:image/png;base64,{input_item}"
                        )
                    else:
                        # Convert PIL Image to base64
                        buffered = BytesIO()
                        input_item.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        images.append(f"data:image/png;base64,{img_str}")
            else:
                raise ValueError(f"Unsupported input type: {type(input_item)}")

        return texts, images

    def _extract_embeddings(self, response) -> list:
        """Extract float embeddings from Cohere response"""
        if hasattr(response, "embeddings"):
            if hasattr(response.embeddings, "float_"):
                return response.embeddings.float_
            return response.embeddings
        return []

    def embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings synchronously using Cohere"""
        if self.sync_client is None:
            raise NotImplementedError(
                "Sync client not provided. Use async_embed instead."
            )

        self._validate_inputs(inputs)

        try:
            inputs = self._prepare_inputs(inputs)
            token_count = self._count_tokens(inputs)
            self._handle_rate_limits_sync(token_count)

            # Convert inputs to Cohere's format
            texts, images = self._prepare_cohere_inputs(inputs, input_type)

            # Log request metrics
            logger.debug(
                f"Making sync request to Cohere {model_id} with "
                f"{len(texts)} texts and {len(images)} images"
            )

            # Handle different input types
            if texts and not images:
                response = self.sync_client.embed(
                    texts=texts,
                    model=model_id,
                    input_type=input_type or "classification",
                    embedding_types=["float"],
                )
                embeddings = self._extract_embeddings(response)
                detected_type = "text"
            elif images and not texts:
                response = self.sync_client.embed(
                    model=model_id,
                    input_type="image",
                    images=images,
                    embedding_types=["float"],
                )
                embeddings = self._extract_embeddings(response)
                detected_type = "image"
            else:
                # For mixed inputs, we need to make separate calls and combine results
                text_response = (
                    self.sync_client.embed(
                        texts=texts,
                        model=model_id,
                        input_type=input_type or "classification",
                        embedding_types=["float"],
                    )
                    if texts
                    else None
                )
                image_response = (
                    self.sync_client.embed(
                        model=model_id,
                        input_type="image",
                        images=images,
                        embedding_types=["float"],
                    )
                    if images
                    else None
                )

                text_embeddings = (
                    self._extract_embeddings(text_response) if text_response else []
                )
                image_embeddings = (
                    self._extract_embeddings(image_response) if image_response else []
                )
                embeddings = text_embeddings + image_embeddings
                detected_type = "multimodal"
                # Combine responses for raw_response field
                response = {
                    "text_response": text_response,
                    "image_response": image_response,
                    "embeddings": embeddings,
                }

            return EmbeddingResponse(
                embeddings=embeddings,
                total_tokens=token_count,
                model_id=model_id,
                input_type=detected_type,
                raw_response=response,
            )

        except Exception as e:
            self._handle_api_error_sync(e, "Cohere embedding generation")

    async def async_embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings asynchronously using Cohere"""
        if self.async_client is None:
            raise NotImplementedError("Async client not provided. Use embed instead.")

        self._validate_inputs(inputs)

        try:
            inputs = self._prepare_inputs(inputs)
            token_count = self._count_tokens(inputs)
            await self._handle_rate_limits(token_count)

            # Convert inputs to Cohere's format
            texts, images = self._prepare_cohere_inputs(inputs, input_type)

            # Log request metrics
            logger.debug(
                f"Making async request to Cohere {model_id} with "
                f"{len(texts)} texts and {len(images)} images"
            )

            # Handle different input types
            if texts and not images:
                response = await self.async_client.embed(
                    texts=texts,
                    model=model_id,
                    input_type=input_type or "classification",
                    embedding_types=["float"],
                )
                embeddings = self._extract_embeddings(response)
                detected_type = "text"
            elif images and not texts:
                response = await self.async_client.embed(
                    model=model_id,
                    input_type="image",
                    images=images,
                    embedding_types=["float"],
                )
                embeddings = self._extract_embeddings(response)
                detected_type = "image"
            else:
                # For mixed inputs, we need to make separate calls and combine results
                text_response = (
                    await self.async_client.embed(
                        texts=texts,
                        model=model_id,
                        input_type=input_type or "classification",
                        embedding_types=["float"],
                    )
                    if texts
                    else None
                )
                image_response = (
                    await self.async_client.embed(
                        model=model_id,
                        input_type="image",
                        images=images,
                        embedding_types=["float"],
                    )
                    if images
                    else None
                )

                text_embeddings = (
                    self._extract_embeddings(text_response) if text_response else []
                )
                image_embeddings = (
                    self._extract_embeddings(image_response) if image_response else []
                )
                embeddings = text_embeddings + image_embeddings
                detected_type = "multimodal"
                # Combine responses for raw_response field
                response = {
                    "text_response": text_response,
                    "image_response": image_response,
                    "embeddings": embeddings,
                }

            return EmbeddingResponse(
                embeddings=embeddings,
                total_tokens=token_count,
                model_id=model_id,
                input_type=detected_type,
                raw_response=response,
            )

        except Exception as e:
            await self._handle_api_error(e, "Cohere embedding generation")
