from typing import Optional
from project_types.embedding_provider import (
    EmbeddingProvider,
    EmbeddingResponse,
    InputType,
)
from utils.types import NotGiven, NOT_GIVEN


class EmbeddingModel:
    """
    A service class for generating embeddings through standardized providers.

    This class provides an interface for generating embeddings from various input types
    (text, images, or text+image pairs) with rate limiting handled by the specific
    provider implementations.
    """

    def __init__(self, provider: EmbeddingProvider):
        """
        Initialize the Embeddings service.

        Args:
            provider (EmbeddingProvider): The embedding provider instance.
        """
        self.provider = provider

    def embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] | NotGiven = NOT_GIVEN,
        batch_size: Optional[int] | NotGiven = NOT_GIVEN,
        truncate: Optional[bool] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
    ) -> EmbeddingResponse:
        """
        Generate embeddings for the given inputs.

        This method supports various input types:
        - Single text string
        - Single image (PIL Image or base64 string)
        - Text + Image pair
        - List of any of the above

        Args:
            inputs: The input(s) to embed. Can be:
                - str: Text to embed
                - PIL.Image: Image to embed
                - Tuple[str, Union[PIL.Image, str]]: Text + Image pair
                - List of any of the above
            model_id (str): The identifier for the model to use.
            input_type (Optional[str], optional): Hint about the input type.
            batch_size (Optional[int], optional): Number of inputs to process at once.
            truncate (Optional[bool], optional): Whether to truncate inputs exceeding max length.
            user (str, optional): User identifier for rate limiting and logging.

        Returns:
            EmbeddingResponse containing the generated embeddings and metadata.

        Raises:
            ValueError: If the input type is invalid
            Various provider-specific exceptions for API errors
        """
        return self.provider.embed(
            inputs=inputs,
            model_id=model_id,
            input_type=input_type,
            batch_size=batch_size,
            truncate=truncate,
            user=user,
        )

    async def async_embed(
        self,
        inputs: InputType,
        model_id: str,
        input_type: Optional[str] | NotGiven = NOT_GIVEN,
        batch_size: Optional[int] | NotGiven = NOT_GIVEN,
        truncate: Optional[bool] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
    ) -> EmbeddingResponse:
        """
        Asynchronously generate embeddings for the given inputs.

        This method supports the same input types as the synchronous version:
        - Single text string
        - Single image (PIL Image or base64 string)
        - Text + Image pair
        - List of any of the above

        Args:
            inputs: The input(s) to embed. Can be:
                - str: Text to embed
                - PIL.Image: Image to embed
                - Tuple[str, Union[PIL.Image, str]]: Text + Image pair
                - List of any of the above
            model_id (str): The identifier for the model to use.
            input_type (Optional[str], optional): Hint about the input type.
            batch_size (Optional[int], optional): Number of inputs to process at once.
            truncate (Optional[bool], optional): Whether to truncate inputs exceeding max length.
            user (str, optional): User identifier for rate limiting and logging.

        Returns:
            EmbeddingResponse containing the generated embeddings and metadata.

        Raises:
            ValueError: If the input type is invalid
            Various provider-specific exceptions for API errors
        """
        return await self.provider.async_embed(
            inputs=inputs,
            model_id=model_id,
            input_type=input_type,
            batch_size=batch_size,
            truncate=truncate,
            user=user,
        )
