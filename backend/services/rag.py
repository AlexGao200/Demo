import os
import re
import urllib.parse
from collections.abc import Generator
from typing import Any, Optional
from nltk.tokenize import sent_tokenize
from enum import Enum
import cohere

from difflib import SequenceMatcher
from flask import current_app
import uuid

import fitz  # pymupdf
from loguru import logger
from utils.error_handlers import log_error, create_error_response
from utils.text_formatting import remove_non_latin_chars, remove_whitespace_and_returns
from services.s3_service import S3Service
from services.elasticsearch_service import VectorStore


# nltk.download("punkt")

from pydantic import BaseModel


class RelevanceInfoSet(BaseModel):
    is_relevant: list[bool]


class GenerationStrategy(str, Enum):
    TEXT_ONLY = "text_only"
    IMAGES_ONLY = "images_only"
    INTERLEAVED = "interleaved"


class Provider(str, Enum):
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OPENAI_COMPATIBLE = "openai"


class ChatPDF:
    def __init__(
        self,
        llm_providers: dict[str, Any],
        prompt,
        vector_store: VectorStore,
        s3_service: S3Service,
        reranker: cohere.ClientV2,
        dims,
    ):
        self.llm_providers = llm_providers
        self.s3_service = s3_service
        self.dims = dims
        self.retriever = vector_store.as_retriever()
        self.prompt = prompt
        self.reranker = reranker
        logger.info("ChatPDF initialized with model and vector store.")

    def generate_chat_title(self, query):
        """Generate a concise and descriptive title for a chat based on the initial query."""
        try:
            messages = [
                {
                    "role": "user",
                    "content": f"Generate a concise and descriptive title for the following query: '{query}' in the format **Your Title Here**.",
                }
            ]
            response = self.llm_providers["groq"].invoke(
                messages, model_id="llama-3.1-8b-instant"
            )
            if isinstance(response, dict) and "error" in response:
                raise ValueError(f"Model error: {response['error']}")

            # Assuming the response is in the format **Title**
            if hasattr(response, "content"):
                title = response.content.strip()  # type: ignore
            else:
                title = str(response).strip()

            # Extract title between ** **
            title_match = re.search(r"\*\*(.*?)\*\*", title)
            if title_match:
                return title_match.group(1).strip()
            else:
                raise ValueError("Failed to parse title from response")
        except Exception as e:
            error_message, stack_trace = log_error(e, "Error generating chat title")
            return None

    def download_and_highlight_pdf(self, s3_file_url: str, section: dict) -> dict:
        """
        Downloads a PDF from S3, highlights specified sections, and returns the path to the highlighted PDF.
        """
        try:
            local_file_path = self.s3_service.download_pdf(
                current_app.config.get("AWS_S3_BUCKET_NAME"), s3_file_url
            )
            if not local_file_path:
                return create_error_response("Failed to download PDF from S3 URL")

            highlighted_pdf_path = ChatPDF.highlight_text_in_pdf(
                local_file_path, section
            )
            if not highlighted_pdf_path:
                return create_error_response("Failed to generate highlighted PDF")

            return {"highlighted_pdf_path": highlighted_pdf_path}
        except Exception as e:
            error_message, stack_trace = log_error(
                e, "Error in download_and_highlight_pdf"
            )
            return create_error_response(error_message, stack_trace)

    def format_content_for_llm(
        self,
        docs: list[dict],
        strategy: GenerationStrategy = GenerationStrategy.TEXT_ONLY,
    ) -> list[dict]:
        """Format content based on the chosen generation strategy."""
        formatted_content = []

        def format_image_upload_dictionary(base64_image: str, provider: Provider):
            if provider == Provider.ANTHROPIC:
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "jpeg",
                        "data": base64_image,
                    },
                }
            elif provider == Provider.GROQ or provider == Provider.OPENAI_COMPATIBLE:
                return {
                    "type": "image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                }
            raise

        for doc in docs:
            metadata = doc["metadata"]

            if strategy == GenerationStrategy.TEXT_ONLY:
                formatted_content.append(
                    {
                        "type": "text",
                        "text": remove_non_latin_chars(
                            remove_whitespace_and_returns(
                                "Document title:"
                                + metadata["section_title"]
                                + "Document content: "
                                + metadata["section_text"]
                            )
                        ),
                    }
                )

            elif strategy == GenerationStrategy.IMAGES_ONLY:
                if "page_images" in metadata and metadata["page_images"]:
                    for image in metadata["page_images"]:
                        # For Anthropic models
                        if self.llm_providers.get("anthropic"):
                            image_content = format_image_upload_dictionary(
                                image, Provider.ANTHROPIC
                            )
                            if image_content:
                                formatted_content.append(image_content)

                        # For OpenAI-compatible models (including Llama)
                        if self.llm_providers.get("hyperbolic"):
                            model_id = self.llm_providers["hyperbolic"].model_id
                            image_content = format_image_upload_dictionary(
                                image, Provider.OPENAI_COMPATIBLE, model_id
                            )
                            if image_content:
                                formatted_content.append(image_content)

            elif strategy == GenerationStrategy.INTERLEAVED:
                # Add text content
                formatted_content.append(
                    {
                        "type": "text",
                        "text": remove_non_latin_chars(
                            remove_whitespace_and_returns(
                                "Document title:"
                                + metadata["section_title"]
                                + "Document content: "
                                + metadata["section_text"]
                            )
                        ),
                    }
                )
                # Add associated images
                if "page_images" in metadata and metadata["page_images"]:
                    for image in metadata["page_images"]:
                        formatted_content.append(
                            {
                                "type": "image",
                                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                            }
                        )

        return formatted_content

    def stream_process_query(
        self,
        query: str,
        chat_id: str,
        index_names: list[str],
        filter_dimensions: dict[str, Any] = None,
        document_titles: Optional[list[str]] = None,
        generation_strategy: GenerationStrategy = GenerationStrategy.TEXT_ONLY,
        conversation_history: Optional[list[dict]] = None,
    ) -> Generator:
        """
        Process a query and stream the response, including relevant document retrieval.
        """
        try:
            if not self.retriever:
                raise ValueError("Retriever is not initialized")

            logger.info(f"Index name: {index_names}")
            logger.info(f"Document titles filter: {document_titles}")
            logger.info(f"Using generation strategy: {generation_strategy}")

            # Ensure document_titles is properly formatted if provided
            if document_titles:
                if isinstance(document_titles, str):
                    document_titles = [document_titles]
                elif not isinstance(document_titles, list):
                    logger.warning(f"Invalid document_titles format: {document_titles}")
                    document_titles = None
                elif not all(isinstance(title, str) for title in document_titles):
                    logger.warning("Invalid document title type in list")
                    document_titles = None
                elif not document_titles:  # Empty list
                    document_titles = None

            docs = self.retriever.get_relevant_documents(
                query,
                index_names=index_names,
                filter_dimensions=filter_dimensions,
                document_titles=document_titles,
                visibility=None,
            )

            if not docs:
                logger.warning("No documents retrieved.")
                yield {"type": "error", "text": "No documents retrieved."}
                return

            logger.info(
                f"docs: {docs}, type: {type(docs)}, total {len(docs)} documents."
            )

            logger.info(f"First unique doc retrieved:{docs[0]}")
            docs = list(
                {
                    (doc["metadata"]["file_url"], doc["metadata"]["section_text"]): doc
                    for doc in docs
                }.values()
            )

            logger.info(f"Number of unique docs: {len(docs)}")

            docs_formatted_for_rerank = [
                f"<title>{doc['metadata']['section_title']}</title>"
                + f"<text>{doc['metadata']['section_text']}</text>"
                for doc in docs
            ]

            relevance_data = self.reranker.rerank(
                model="rerank-v3.5",
                query=query,
                documents=docs_formatted_for_rerank,
                top_n=3,
                return_documents=False,
            )

            logger.info(relevance_data)
            logger.info(relevance_data.__dict__)
            relevance_data = relevance_data.results
            docs = [docs[result.index] for result in relevance_data]

            # Format content based on generation strategy
            formatted_content = self.format_content_for_llm(docs, generation_strategy)

            # Prepare conversation history
            formatted_messages = []
            if conversation_history:
                formatted_messages.extend(conversation_history)

            # Construct prompt based on strategy
            if generation_strategy == GenerationStrategy.TEXT_ONLY:
                context = "\n------------------------------------------------------------------------------------------------\n".join(
                    [
                        content["text"]
                        for content in formatted_content
                        if content["type"] == "text"
                    ]
                )
                formatted_messages.append(
                    {
                        "role": "user",
                        "content": self.prompt.format(question=query, context=context),
                    }
                )
                stream = self.llm_providers["anthropic"].invoke(
                    formatted_messages, model_id="claude-3-5-sonnet-latest", stream=True
                )
            else:
                # For image-based strategies, use Anthropic's Claude
                formatted_query = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Based on the provided content, answer this question: {query}",
                            },
                            *formatted_content,
                            {"type": "text", "text": "Answer:"},
                        ],
                    }
                ]
                stream = self.llm_providers["anthropic"].invoke(
                    formatted_query, model_id="claude-3-5-sonnet-latest", stream=True
                )

            full_response_text = ""
            logger.debug("Starting to process stream chunks")
            for chunk in stream:
                # Handle both OpenAI-style and Groq-style streaming responses
                content = None
                if isinstance(chunk, str):
                    # Direct string content from Groq
                    content = chunk
                elif hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    # OpenAI-style response
                    if hasattr(chunk.choices[0], "delta") and hasattr(
                        chunk.choices[0].delta, "content"
                    ):
                        content = chunk.choices[0].delta.content
                    elif hasattr(chunk.choices[0], "message") and hasattr(
                        chunk.choices[0].message, "content"
                    ):
                        content = chunk.choices[0].message.content

                if content not in [False, None, ""]:
                    logger.info(f"Yielding chunk: {content}")
                    full_response_text += content
                    yield {"type": "content", "text": content}
            logger.debug("Finished processing stream chunks")

            yield self.process_cites(
                full_response_text, docs, index_names, chat_id, filter_dimensions
            )
        except Exception as e:
            error_message, stack_trace = log_error(
                e, "Error during stream query processing"
            )
            yield {"type": "error", "text": error_message}

    def process_cites(
        self, full_response_text, unique_docs, index_names, chat_id, filter_dimensions
    ):
        try:
            cited_sections = []
            seen_citations = (
                set()
            )  # TODO Hash the citation dictionary for more efficient checks

            for idx, doc in enumerate(unique_docs):
                citation_text = remove_non_latin_chars(
                    remove_whitespace_and_returns(
                        doc["metadata"]["section_text"].replace("\n", " ")
                    )
                )

                # Check if the citation is unique
                if citation_text in seen_citations:
                    logger.info(
                        f"Duplicate citation found, skipping: {citation_text[:100]}..."
                    )
                    continue

                # Add the citation text to the seen set
                seen_citations.add(citation_text)
                fd = doc["metadata"].get("filter_dimensions", {})
                if fd:
                    logger.info(f"FD: {fd}")
                    fd = {
                        item["dimension_name"]: item["values"] for item in fd
                    }  # FIXME fix this at the embedding level if possible
                section = {
                    "text": citation_text,
                    "file_url": doc["metadata"]["file_url"],
                    "title": doc["metadata"].get("title", f"Document {idx + 1}"),
                    "section_title": doc["metadata"].get("section_title", "unknown"),
                    "pages": doc["metadata"].get("pages", []),
                    "index_names": doc["metadata"].get("index_names", []),
                    "organization": doc["metadata"].get("creator_org", "unknown"),
                    "filter_dimensions": fd,
                    "preview": self.truncate_text(citation_text, 300),
                    "index_display_name": doc["metadata"].get("index_display_name"),
                    "nominal_creator_name": doc["metadata"].get("nominal_creator_name"),
                }

                cited_sections.append(section)

                result = self.download_and_highlight_pdf(
                    doc["metadata"]["file_url"], section
                )

                highlighted_pdf_path = result.get("highlighted_pdf_path")
                if highlighted_pdf_path:
                    file_name = os.path.basename(highlighted_pdf_path)

                    # Ensure the page number is safely accessed
                    page_number = doc["metadata"].get("pages", [1])[
                        0
                    ]  # Default to page 1 if no pages found or if pages array is empty

                    # Generate the document link correctly with the page number
                    encoded_file_name = urllib.parse.quote(file_name)
                    highlighted_file_url = f"{current_app.config.get('FRONTEND_BASE_URL')}/document/backend/tmp/{encoded_file_name}/{page_number}?chat_id={chat_id}"
                    logger.info(f"Generated document link: {highlighted_file_url}")
                    section["highlighted_file_url"] = highlighted_file_url
                else:
                    logger.warning(
                        f"Failed to generate highlighted PDF for document: {doc['metadata']['title']}"
                    )

            return {
                "type": "citations",
                "cited_sections": cited_sections,
                "index_names": index_names,
                "full_text": full_response_text,
                "filter_dimensions": filter_dimensions,
            }

        except Exception as e:
            error_message, stack_trace = log_error(
                e, "Error during processing citations"
            )
            return create_error_response(error_message, stack_trace)

    @staticmethod
    def highlight_text_in_pdf(
        file_path: str,
        cited_section: dict,
        match_threshold=0.3,
        context_window=5,
        loose_match_threshold=0.7,
    ):
        try:
            document = fitz.open(file_path)
            cited_section_texts = []
            logger.info(f"Starting to highlight PDF: {file_path}.")

            text_to_find = cited_section["text"]
            page_num = cited_section["pages"][0] - 1  # Adjust for zero-based index

            if page_num < 0 or page_num >= len(document):
                logger.warning(
                    f"Page number {page_num + 1} is out of range for the document."
                )
                return file_path

            page = document[page_num]
            words = page.get_text("words")  # Get words as (x0, y0, x1, y1, word) tuples
            found = False
            final_match_words = text_to_find.split()
            target_len = len(final_match_words)

            logger.info(
                f"Attempting to highlight words with context for '{text_to_find}' on page {page_num + 1}"
            )

            # First, try contextual matching for structured text
            for i in range(len(words) - target_len + 1):
                segment = " ".join([words[j][4] for j in range(i, i + target_len)])

                if (
                    SequenceMatcher(None, segment, text_to_find).ratio()
                    >= match_threshold
                ):
                    surrounding_words = [
                        words[j][4]
                        for j in range(
                            max(i - context_window, 0),
                            min(i + target_len + context_window, len(words)),
                        )
                    ]

                    match_count = sum(
                        1
                        for w, tw in zip(surrounding_words, final_match_words)
                        if w == tw
                    )
                    context_match_ratio = match_count / target_len

                    if context_match_ratio >= match_threshold:
                        for j in range(i, i + target_len):
                            rect = fitz.Rect(words[j][:4])
                            highlight_annot = page.add_highlight_annot(rect)
                            highlight_annot.set_colors(stroke=[1, 1, 0])
                            highlight_annot.set_opacity(0.5)
                            highlight_annot.update()
                            logger.debug(
                                f"Highlighting word '{words[j][4]}' in rectangle {rect}"
                            )

                        cited_section_texts.append(
                            f"Highlighted phrase '{segment}' on page {page_num + 1}"
                        )
                        logger.debug(
                            f"Successfully highlighted segment '{segment}' on page {page_num + 1}"
                        )
                        found = True
                        break

            # Fallback: Loose keyword matching for unstructured text if no match was found
            if not found:
                logger.warning(
                    f"No context match found. Attempting loose keyword match for '{text_to_find}'."
                )
                keywords = text_to_find.split()
                keyword_matches = []

                for keyword in keywords:
                    for word in words:
                        if (
                            SequenceMatcher(None, word[4], keyword).ratio()
                            >= loose_match_threshold
                        ):
                            x0, y0, x1, y1 = word[:4]
                            rect = fitz.Rect(x0, y0, x1, y1)
                            highlight_annot = page.add_highlight_annot(rect)
                            highlight_annot.set_colors(stroke=[1, 1, 0])
                            highlight_annot.set_opacity(0.5)
                            highlight_annot.update()
                            logger.debug(
                                f"Highlighted isolated word '{word[4]}' in rectangle {rect}"
                            )
                            keyword_matches.append(word[4])
                            found = True

                if found:
                    cited_section_texts.append(
                        f"Loosely highlighted words '{', '.join(keyword_matches)}' on page {page_num + 1}"
                    )

            if not found:
                logger.warning(
                    f"No match found for '{text_to_find}' on page {page_num + 1}"
                )

            new_file_path = os.path.join(
                current_app.config.get("TMP_DIR"),
                os.path.basename(file_path).replace(
                    ".pdf", f"_highlighted{str(uuid.uuid4())[:8]}.pdf"
                ),
            )

            document.save(new_file_path, garbage=4, deflate=True, clean=True)
            logger.info(f"Highlighted PDF saved at: {new_file_path}")
            return new_file_path

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error highlighting text in PDF")
            return file_path

    @staticmethod
    def split_into_sentences(text):
        """Split the input text into a list of sentences using nltk's sentence tokenizer."""
        sentences = sent_tokenize(text)
        return sentences

    @staticmethod
    def find_best_match_with_context(page_text, query, context_range=2):
        best_score = 0
        best_match = ""
        best_start = 0
        best_end = 0

        for i in range(len(page_text)):
            context_text = " ".join(
                page_text[
                    max(i - context_range, 0) : min(
                        i + context_range + 1, len(page_text)
                    )
                ]
            )

            # Log the query and context being matched
            logger.debug(f"Query: {query}")
            logger.debug(f"Context text: {context_text}")

            # Using SequenceMatcher for similarity scoring
            score = SequenceMatcher(None, context_text, query).ratio()

            if score > best_score:
                best_score = score
                best_match = context_text
                best_start = max(i - context_range, 0)
                best_end = min(i + context_range + 1, len(page_text))

        # Log the best match found
        logger.debug(f"Best match found: {best_match} with score {best_score}")

        return best_match, best_score, best_start, best_end

    @staticmethod
    def expand_match(
        page_text, start, end, query, best_match, best_score, max_expand=2
    ):
        """
        Expands the match to adjacent sentences if the current match is not sufficient.
        """
        for expand in range(1, max_expand + 1):
            if start - expand >= 0:
                new_match = " ".join(page_text[start - expand : end])
                new_score = SequenceMatcher(None, new_match, query).ratio()
                if new_score > best_score:
                    best_score = new_score
                    best_match = new_match

            if end + expand <= len(page_text):
                new_match = " ".join(page_text[start : end + expand])
                new_score = SequenceMatcher(None, new_match, query).ratio()
                if new_score > best_score:
                    best_score = new_score
                    best_match = new_match

        return best_match, best_score

    @staticmethod
    def ensure_full_sentence_start(citation_text):
        """Adjusts the citation text to start at the beginning of a sentence."""
        sentences = sent_tokenize(citation_text)
        if sentences:
            return sentences[0]  # Return the first sentence
        return citation_text

    @staticmethod
    def truncate_text(text: str, max_length: int) -> str:
        """Truncate text to specified length, ending at a sentence boundary."""
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        last_sentence_end = truncated.rfind(".")

        return (
            f"{truncated[:last_sentence_end + 1]}..."
            if last_sentence_end != -1
            else f"{truncated}..."
        )
