"""
This module provides functionality for processing and ingesting documents into a vector store.
It includes text extraction, segmentation, embedding generation, and storage of document sections.
"""

from loguru import logger
from utils.error_handlers import log_error
import hashlib
from models.user import User
from models.organization import Organization
from models.file_metadata import FileMetadata
from models.index_registry import IndexRegistry
from services.document_processing_strategies import (
    DocumentProcessingStrategy,
    SegmentationStrategy,
)
from services.embedding_strategies import EmbeddingStrategy, CohereEmbeddingStrategy
from typing import Any, Optional, Callable
import unicodedata
import re


def slugify(text):
    """
    Convert text into a URL-friendly slug.
    """
    text = str(text).lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"[-\s]+", "-", text.strip())
    return text


class DocumentProcessor:
    """
    A class for processing documents, extracting text, generating embeddings, and storing in a vector database.

    This class handles the entire pipeline of document processing, from text extraction to
    storage in a vector database, using configurable processing and embedding strategies.

    Attributes:
        llm_providers (dict[str, Any]): dictionary of LLM providers for different operations
        vector_store (VectorStore): The vector store for storing document embeddings.
        dims (int): The dimensionality of the embeddings.
        processing_strategy (DocumentProcessingStrategy): Strategy for processing documents
        embedding_strategy (EmbeddingStrategy): Strategy for generating embeddings
    """

    def __init__(
        self,
        llm_providers: dict[str, Any],
        vector_store: Any,
        dims: int,
        processing_strategy: Optional[DocumentProcessingStrategy] = None,
        embedding_strategy: Optional[EmbeddingStrategy] = None,
    ):
        """
        Initialize the DocumentProcessor with necessary components and strategies.

        Args:
            llm_providers (dict[str, Any]): dictionary of LLM providers for different operations
            vector_store (VectorStore): The vector store for storing document embeddings.
            dims (int): The dimensionality of the embeddings.
            processing_strategy (Optional[DocumentProcessingStrategy]): Strategy for document processing
            embedding_strategy (Optional[EmbeddingStrategy]): Strategy for generating embeddings
        """
        self.llm_providers = llm_providers
        self.vector_store = vector_store
        self.dims = dims

        # Set default strategies if none provided
        if processing_strategy is None:
            # Assuming treeseg_configs is passed through llm_providers for backward compatibility
            processing_strategy = SegmentationStrategy(
                treeseg_configs=llm_providers.get("treeseg_configs"),
                embeddings_providers=llm_providers.get("embedding_model"),
            )
        if embedding_strategy is None:
            embedding_strategy = CohereEmbeddingStrategy(
                embeddings_providers=llm_providers.get("embedding_model")
            )

        self.processing_strategy = processing_strategy
        self.embedding_strategy = embedding_strategy

    def calculate_document_hash(self, file_path: str, index_name: str) -> str:
        """
        Calculate a hash for the document file, including the index name.

        Args:
            file_path (str): The path to the document file.
            index_name (str): The name of the index.

        Returns:
            str: The calculated hash of the document.
        """
        try:
            with open(file_path, "rb") as file:
                file_hash = hashlib.sha256()
                chunk = file.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = file.read(8192)

                # Include the index name in the hash calculation
                file_hash.update(index_name.encode("utf-8"))

            return file_hash.hexdigest()
        except Exception as e:
            log_error(e, "Error calculating document hash")
            return ""

    async def ingest(
        self,
        file_path: str,
        file_url: str,
        title: str,
        thumbnail_urls: list[str],
        index_names: list[str],
        file_visibility: str,
        originating_user_id: str,
        filter_dimensions: dict,
        nominal_creator_name: str = "",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Ingest a document into the vector store and create or update FileMetadata objects.

        This method processes the document using the configured strategies, generates embeddings,
        and stores the segments in the vector store.

        Args:
            file_path (str): The path to the document file.
            file_url (str): The URL where the document can be accessed.
            title (str): The title of the document.
            thumbnail_urls: URLs for document thumbnails.
            index_names (list[str]): The names of the indices in the vector store.
            file_visibility (str): The visibility of the document ("public" or "private").
            originating_user_id (str): ID of user who originated the document.
            filter_dimensions (dict): A dictionary of filter dimensions and their values.
            nominal_creator_name (str): The display name of the owner organization.
            progress_callback (Optional[Callable[[float, str], None]]): Callback for progress updates.
                First argument is progress (0.0-1.0), second is current step description.
        """
        try:
            logger.info(f"Starting the ingestion process for indices {index_names}.")

            def update_progress(progress: float, step: str):
                if progress_callback:
                    progress_callback(progress, step)

            # Process the document using the configured strategy (0.0 -> 0.4)
            update_progress(0.0, "Starting text extraction")
            processed_sections = await self.processing_strategy.process_document(
                file_path=file_path,
                file_url=file_url,
                title=title,
                filter_dimensions=filter_dimensions,
                nominal_creator_name=nominal_creator_name,
                llm_providers=self.llm_providers,
            )

            if not processed_sections:
                logger.error("No sections were processed from the document.")
                return None

            update_progress(0.4, "Text extraction complete")

            # Generate embeddings for processed sections (0.4 -> 0.8)
            logger.info("Generating embeddings for processed sections.")
            documents_with_embeddings = []
            total_sections = len(processed_sections)

            for i, section in enumerate(processed_sections):
                embedding = await self.embedding_strategy.embed_document(section)
                if embedding:
                    documents_with_embeddings.append(
                        {**section, "embedding": embedding}
                    )
                    # Update progress for each section
                    section_progress = 0.4 + (0.4 * ((i + 1) / total_sections))
                    update_progress(
                        section_progress,
                        f"Generating embeddings ({i + 1}/{total_sections})",
                    )
                else:
                    logger.info(
                        f"No embedding generated for section {section}. Embedding: {embedding}"
                    )

            logger.info(
                f"Generated embeddings for {len(documents_with_embeddings)} sections."
            )

            # Index documents (0.8 -> 1.0)
            update_progress(0.8, "Starting vector store indexing")

            # Process each index separately
            for index_name in index_names:
                # Calculate document hash for this index
                document_hash = self.calculate_document_hash(file_path, index_name)

                # Check if document already exists in this index
                existing_doc = FileMetadata.objects(
                    document_hash=document_hash, index_names=[index_name]
                ).first()
                index_display_name = IndexRegistry.objects.get(
                    index_name=index_name
                ).index_display_name

                if existing_doc:
                    logger.info(
                        f"Document with hash {document_hash} already exists in index {index_name}. Updating metadata."
                    )
                    # Update existing document metadata
                    args = {
                        "title": title,
                        "s3_url": file_url,
                        "thumbnail_urls": thumbnail_urls,
                        "visibility": file_visibility,
                        "originating_user": User.objects(
                            id=str(originating_user_id)
                        ).first(),
                        "organizations": [
                            Organization.objects(index_name=index_name).first()
                        ],
                        "filter_dimensions": filter_dimensions,
                        "is_deleted": False,
                        "index_display_name": index_display_name,
                    }
                    if nominal_creator_name:
                        args["nominal_creator_name"] = nominal_creator_name
                    elif existing_doc.nominal_creator_name:
                        args["nominal_creator_name"] = existing_doc.nominal_creator_name

                    existing_doc.update(**args)
                    doc = existing_doc
                else:
                    logger.info(
                        f"Processing new document with hash {document_hash} for index {index_name}"
                    )
                    # Create and save new FileMetadata object for this index
                    args = {
                        "name": title,
                        "s3_url": file_url,
                        "document_hash": document_hash,
                        "title": title,
                        "index_names": [index_name],
                        "thumbnail_urls": thumbnail_urls,
                        "visibility": file_visibility,
                        "originating_user": User.objects(
                            id=str(originating_user_id)
                        ).first(),
                        "organizations": [
                            Organization.objects(index_name=index_name).first()
                        ],
                        "filter_dimensions": filter_dimensions,
                        "index_display_name": index_display_name,
                    }
                    if nominal_creator_name:
                        args["nominal_creator_name"] = nominal_creator_name

                    doc = FileMetadata(**args)
                    doc.save()
                    logger.info(
                        f"New FileMetadata object created and saved for document: {title} in index {index_name}"
                    )

                # Add embeddings to vector store for this index
                for doc_with_embedding in documents_with_embeddings:
                    embedding = doc_with_embedding["embedding"]
                    try:
                        if embedding is None or len(embedding) != self.dims:
                            logger.error(
                                f"Invalid embedding for document: {doc_with_embedding['metadata']}"
                            )
                            continue

                        metadata = doc_with_embedding["metadata"]
                        metadata["contextualized_segment_text"] = doc_with_embedding[
                            "contextualized_segment_text"
                        ]
                        metadata["index_names"] = [index_name]
                        metadata["index_display_name"] = index_display_name

                        logger.debug(
                            f"Adding embedding to vector store for index {index_name}: {metadata}"
                        )

                        self.vector_store.add_embedding(
                            embedding, metadata, index_name=index_name
                        )
                    except Exception as e:
                        log_error(
                            e,
                            f"Error adding document to vector store in index {index_name}",
                        )

            update_progress(1.0, "Vector store indexing complete")

            return {
                "message": "File uploaded and processed successfully.",
                "document_title": title,
                "document_url": file_url,
                "doc_ids": [
                    str(
                        FileMetadata.objects(
                            document_hash=self.calculate_document_hash(
                                file_path, index_name
                            )
                        )
                        .first()
                        .id
                    )
                    for index_name in index_names
                ],
            }

        except Exception as e:
            log_error(e, f"Error during ingestion to index {index_names}")
            return None
