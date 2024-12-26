"""
This module provides different strategies for generating embeddings from processed documents.
It allows for easy switching between different embedding providers and modalities.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np
from utils.error_handlers import log_error
from utils.pdf_utils import extract_and_process_pdf_pages


class EmbeddingStrategy(ABC):
    """
    Abstract base class for embedding strategies.
    Defines how documents should be embedded for vector search.
    """

    @abstractmethod
    async def embed_document(self, document: dict[str, Any]) -> Optional[list[float]]:
        """
        Generate embeddings for a processed document.

        Args:
            document: Dictionary containing processed document data and metadata

        Returns:
            Optional[list[float]]: The generated embedding vector, or None if embedding fails
        """
        pass


class CohereEmbeddingStrategy(EmbeddingStrategy):
    """
    Strategy for generating text-only embeddings using Cohere's API.
    Implements batching for improved efficiency.
    """

    def __init__(self, embeddings_providers: dict):
        self.embedding_model = embeddings_providers["cohere"]
        self._text_batch = []
        self._batch_size = 96  # Cohere's recommended batch size
        self._document_vectors = {}

    async def _process_batch(self) -> dict[str, list[float]]:
        """
        Process accumulated text batch and return embeddings.
        """
        if not self._text_batch:
            return {}

        try:
            response = await self.embedding_model.async_embed(
                self._text_batch,
                input_type="search_document",
                model_id="embed-english-v3.0",
                batch_size=self._batch_size,
            )

            # Create mapping of text to embedding
            text_to_embedding = {}
            for text, embedding in zip(self._text_batch, response.embeddings):
                text_to_embedding[text] = embedding

            # Clear the batch
            self._text_batch = []

            return text_to_embedding

        except Exception as e:
            log_error(e, "Error processing Cohere embedding batch")
            self._text_batch = []  # Clear batch on error
            return {}

    async def embed_document(self, document: dict[str, Any]) -> Optional[list[float]]:
        try:
            text = document.get("contextualized_segment_text")
            if not text:
                return None

            # Check if we already have the embedding
            if text in self._document_vectors:
                return self._document_vectors[text]

            # Add to batch
            self._text_batch.append(text)

            # Process batch if it reaches the size limit
            if len(self._text_batch) >= self._batch_size:
                embeddings = await self._process_batch()
                self._document_vectors.update(embeddings)
                return embeddings.get(text)

            # If this is the first document, process immediately
            if len(self._text_batch) == 1:
                embeddings = await self._process_batch()
                self._document_vectors.update(embeddings)
                return embeddings.get(text)

            # Otherwise, wait for batch to fill
            return None

        except Exception as e:
            log_error(e, "Error generating Cohere embedding")
            return None


class VoyageEmbeddingStrategy(EmbeddingStrategy):
    """
    Strategy for generating multimodal embeddings using Voyage's API.
    Handles PDF-to-image conversion and embedding generation with efficient batching.
    """

    def __init__(self, embeddings_providers, zoom: float = 3.0):
        self.embedding_model = embeddings_providers["voyage"]
        self.zoom = zoom
        self._document_vectors = {}  # Cache for document vectors
        self._batch_size = 128  # Voyage's recommended batch size

    def _pdf_to_screenshots(self, file_path: str, zoom: float = 1.0) -> list[str]:
        """
        Convert PDF pages to base64 encoded images.

        Args:
            file_path: Path to the PDF file
            zoom: Zoom factor for rendering quality

        Returns:
            list[str]: list of base64 encoded images
        """
        return extract_and_process_pdf_pages(
            file_path=file_path,
            target_width=1568,  # Anthropic's preferred width
            target_height=1568,  # Anthropic's preferred height
            zoom=zoom,
        )

    async def embed_document(self, document: dict[str, Any]) -> Optional[list[float]]:
        try:
            # Get PDF URL and page number from metadata
            metadata = document.get("metadata", {})
            pdf_url = metadata.get("file_url")
            pages = metadata.get("pages", [])
            page_images = metadata.get("page_images", [])

            if not pdf_url or not pages:
                return None

            page_num = pages[0] - 1  # Convert to 0-based index

            # Check if we already have vectors for this document
            if pdf_url not in self._document_vectors:
                # Use page_images if available, otherwise generate them
                if not page_images:
                    page_images = self._pdf_to_screenshots(
                        file_path=pdf_url, zoom=self.zoom
                    )

                # Process images in batches
                document_vectors = []
                for i in range(0, len(page_images), self._batch_size):
                    batch = page_images[i : i + self._batch_size]
                    batch_response = await self.embedding_model.async_embed(
                        inputs=[[page] for page in batch],
                        model_id="voyage-multimodal-3",
                        input_type="document",
                    )
                    document_vectors.extend(batch_response.embeddings)

                # Cache the vectors
                self._document_vectors[pdf_url] = np.array(document_vectors)

            # Return the vector for the specific page
            document_vectors = self._document_vectors[pdf_url]
            if 0 <= page_num < len(document_vectors):
                return document_vectors[page_num].tolist()

            return None

        except Exception as e:
            log_error(e, "Error generating Voyage multimodal embedding")
            return None
