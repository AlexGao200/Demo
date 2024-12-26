"""
This module provides different strategies for processing documents before embedding.
It separates document processing concerns from embedding concerns while maintaining
consistent metadata structure with the existing implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional
from project_types.llm_provider import Message
import fitz  # PyMuPDF
from treeseg.treeseg import TreeSeg
from utils.error_handlers import log_error
from utils.pdf_utils import extract_and_process_pdf_pages
from loguru import logger


class DocumentProcessingStrategy(ABC):
    """
    Abstract base class for document processing strategies.
    Defines how documents should be broken down for embedding.
    """

    @abstractmethod
    async def process_document(
        self,
        file_path: str,
        file_url: str,
        title: str,
        filter_dimensions: dict[str, Any],
        nominal_creator_name: str,
        llm_providers: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Process a document into chunks ready for embedding.

        Args:
            file_path: Path to the document file
            file_url: URL where the document is accessible
            title: Document title
            filter_dimensions: dictionary of filter dimensions and their values
            nominal_creator_name: Display name of the owner organization
            llm_providers: Optional LLM providers for additional processing

        Returns:
            list of dictionaries containing processed chunks with metadata
        """
        pass


class SegmentationStrategy(DocumentProcessingStrategy):
    """
    Strategy that processes documents by segmenting them into logical chunks.
    Uses TreeSeg for intelligent text segmentation.
    """

    def __init__(self, treeseg_configs: TreeSeg, embeddings_providers):
        self.treeseg_configs = treeseg_configs
        self.embedding_model = embeddings_providers["cohere"]

    async def process_document(
        self,
        file_path: str,
        file_url: str,
        title: str,
        filter_dimensions: dict[str, Any],
        nominal_creator_name: str,
        llm_providers: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        try:
            # Extract text and create component mapping
            full_text, component_map = self._extract_text(file_path)
            if not full_text or not component_map:
                return []

            # Extract and process page images
            page_images = extract_and_process_pdf_pages(
                file_path,
                target_width=1568,  # Claude's preferred dimension
                target_height=1568,
                zoom=3.0,  # High quality rendering
            )

            # Segment the text
            sections = await self._segment_text(full_text, component_map)
            full_text_joined = " ".join(full_text)

            # Process each section
            processed_sections = []
            for section in sections:
                if llm_providers and "anthropic" in llm_providers:
                    # Generate title and context if LLM providers are available
                    section_title = await self._generate_section_title(
                        section["text"], llm_providers
                    )
                    context, usage = await self._generate_context(
                        full_text_joined, section["text"], llm_providers
                    )
                    logger.info(
                        f"Generated section title *{section_title}* and context {context}"
                    )
                else:
                    section_title = "Untitled Section"
                    context = ""

                # Get page images for this section
                section_page_images = [
                    page_images[page_num - 1]
                    for page_num in section["pages"]
                    if 0 <= page_num - 1 < len(page_images)
                ]

                processed_sections.append(
                    {
                        "contextualized_segment_text": f"{context}\n\n{section['text']}"
                        if context
                        else section["text"],
                        "metadata": {
                            "file_url": file_url,
                            "section_title": section_title,
                            "title": title,
                            "pages": section["pages"],
                            "page_images": section_page_images,
                            "section_text": section["text"],
                            "filter_dimensions": filter_dimensions,
                            "nominal_creator_name": nominal_creator_name,
                        },
                    }
                )
            logger.info("Processed document sections.")
            return processed_sections
        except Exception as e:
            log_error(e, "Error processing document with SegmentationStrategy")
            return []

    def _extract_text(self, file_path: str) -> Tuple[list[str], list[int]]:
        """Extract text and page mapping from PDF."""
        try:
            document = fitz.open(file_path)
            full_text = []
            component_to_page_map = []

            for page_num in range(len(document)):
                page = document.load_page(page_num)
                page_text = page.get_text("text")
                if page_text:
                    components = page_text.split("\n")
                    full_text.extend(components)
                    component_to_page_map.extend([page_num + 1] * len(components))

            return full_text, component_to_page_map
        except Exception as e:
            log_error(e, "Error extracting text from PDF")
            return [], []

    async def _segment_text(
        self, full_text: list[str], component_map: list[int]
    ) -> list[dict[str, Any]]:
        """Segment text using TreeSeg."""
        try:
            entries = [
                {"composite": comp, "index": idx} for idx, comp in enumerate(full_text)
            ]
            treeseg = TreeSeg(
                configs=self.treeseg_configs,
                entries=entries,
                async_embedding_model=self.embedding_model,
            )
            transitions = await treeseg.segment_meeting(K=1000)

            logger.info("Treeseg segment cuts complete.")

            sections = []
            section_start = 0

            for i, is_transition in enumerate(transitions):
                if is_transition:
                    section_end = i - 1
                    section_text = "\n".join(full_text[section_start : section_end + 1])
                    pages = sorted(set(component_map[section_start : section_end + 1]))
                    sections.append(
                        {
                            "text": section_text,
                            "pages": pages,
                        }
                    )
                    section_start = i

            # Handle the last section
            if section_start < len(full_text):
                section_text = "\n".join(full_text[section_start:])
                pages = sorted(set(component_map[section_start:]))
                sections.append(
                    {
                        "text": section_text,
                        "pages": pages,
                    }
                )
            logger.info("Treeseg segment agglomeration complete.")

            return sections
        except Exception as e:
            log_error(e, "Error segmenting text with TreeSeg")
            return []

    async def _generate_section_title(
        self, section_text: str, llm_providers: dict[str, Any]
    ) -> str:
        """Generate a title for a section using LLM."""
        try:
            messages: list[Message] = [
                {
                    "role": "system",
                    "content": "You summarize medical documents.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate a concise and descriptive title for the following section. "
                        f"Please format the title as follows: 'Title: **Your Title Here**' or 'Title: \"Your Title Here\"'.\n\n"
                        f"{section_text}\n\n"
                        f"Title: **Your Title Here**"
                    ),
                },
            ]

            response = await llm_providers["hyperbolic"].ainvoke(
                messages=messages,
                model_id="meta-llama/Llama-3.2-3B-Instruct",
            )
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            import re

            title_match = re.search(r"\*\*(.*?)\*\*", content)
            if title_match:
                return title_match.group(1).strip()

            title_match = re.search(r"\"(.*?)\"", content)
            if title_match:
                return title_match.group(1).strip()

            return "Untitled Section"
        except Exception as e:
            log_error(e, "Error generating section title")
            return "Untitled Section"

    async def _generate_context(
        self, full_text: str, section_text: str, llm_providers: dict[str, Any]
    ) -> Tuple[str, Any]:
        """Generate context for a section using LLM."""
        try:
            # Create system message with cache_control for both full text and section
            system_messages = [
                {
                    "type": "text",
                    "text": "You are an AI assistant that provides succinct context for document sections.",
                },
                {
                    "type": "text",
                    "text": full_text,
                    "cache_control": {"type": "ephemeral"},
                },
            ]

            messages: list[Message] = [
                {
                    "role": "user",
                    "content": (
                        "Provide a succinct context for this section within the overall document "
                        "for improving search retrieval. Answer only with the succinct context. "
                        f"<section>{section_text}</section>"
                    ),
                }
            ]

            response = await llm_providers["anthropic"].ainvoke(
                messages=messages,
                model_id="claude-3-5-sonnet-latest",
                system_prompts=system_messages,
                max_tokens=200,
                temperature=0.5,
            )

            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            usage = (
                response.raw_response.usage
                if hasattr(response, "raw_response")
                else None
            )

            return content, usage
        except Exception as e:
            log_error(e, "Error generating context")
            return "", type("Usage", (), {"input_tokens": 0, "output_tokens": 0})()


class VoyageDocumentStrategy(DocumentProcessingStrategy):
    """
    Strategy optimized for Voyage's multimodal embedding approach.
    Processes documents by providing URLs and page metadata, letting Voyage
    handle the PDF-to-image conversion internally.
    """

    async def process_document(
        self,
        file_path: str,
        file_url: str,
        title: str,
        filter_dimensions: dict[str, Any],
        nominal_creator_name: str,
        llm_providers: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        try:
            # Extract basic text content for search context
            document = fitz.open(file_path)
            processed_pages = []

            # Extract and process page images
            page_images = extract_and_process_pdf_pages(
                file_path,
                target_width=1568,  # Claude's preferred width
                target_height=1568,  # Claude's preferred height
                zoom=3.0,  # High quality rendering
            )

            for page_num in range(len(document)):
                page = document.load_page(page_num)
                page_text = page.get_text("text")

                if llm_providers and "anthropic" in llm_providers:
                    # Generate title and context if LLM providers are available
                    section_title = await self._generate_section_title(
                        page_text, llm_providers
                    )
                else:
                    section_title = "Untitled Section"

                # Get the page image if available
                page_image = (
                    page_images[page_num] if page_num < len(page_images) else None
                )
                page_image_list = [page_image] if page_image else []

                processed_pages.append(
                    {
                        "contextualized_segment_text": page_text,
                        "metadata": {
                            "file_url": file_url,  # Voyage will use this to fetch and process the PDF
                            "section_title": section_title,
                            "title": title,
                            "pages": [page_num + 1],
                            "page_images": page_image_list,  # Add page image to metadata
                            "section_text": page_text,
                            "filter_dimensions": filter_dimensions,
                            "nominal_creator_name": nominal_creator_name,
                        },
                    }
                )

            return processed_pages
        except Exception as e:
            log_error(e, "Error processing document with VoyageDocumentStrategy")
            return []
