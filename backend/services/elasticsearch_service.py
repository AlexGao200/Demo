import time
from typing import Union, Optional, Any
import os
from loguru import logger
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as es_exceptions
from elasticsearch.helpers import bulk

from utils.error_handlers import log_error
from services.embedding_service import EmbeddingModel

from httpx import ConnectError

elasticsearch_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
elasticsearch_username = os.getenv("ELASTICSEARCH_USER", "elastic")
elasticsearch_password = os.getenv("ELASTICSEARCH_PASSWORD", "z#]6]^a!w:mvEyXE-??n")
use_ssl = os.getenv("ELASTICSEARCH_USE_SSL", "true").lower() == "true"
verify_certs = os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true"
use_auth = os.getenv("ELASTICSEARCH_USE_AUTH", "true").lower() == "true"
use_ssl = os.getenv("ELASTICSEARCH_USE_SSL", "true").lower() == "true"
verify_certs = os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true"
use_auth = os.getenv("ELASTICSEARCH_USE_AUTH", "true").lower() == "true"


def create_elasticsearch_client_with_retries(
    host: str = elasticsearch_host,
    port: int = 9200,
    username: str = elasticsearch_username,
    password: str = elasticsearch_password,
    max_retries: int = 5,
    retry_delay: int = 10,
) -> Elasticsearch:
    """Create an Elasticsearch client with retry logic."""
    logger.info(
        f"Starting connection to Elasticsearch at {host}:{port}"
        + (f" with username: {username}" if use_auth else "")
    )

    for attempt in range(max_retries):
        try:
            # Update the client configuration
            config = {
                "hosts": [f"{'https' if use_ssl else 'http'}://{host}:{port}"],
                "request_timeout": 30,
                "retry_on_timeout": True,
                "max_retries": 3,
            }
            if use_auth:
                config["basic_auth"] = (username, password)
            if use_ssl:
                config.update(
                    {
                        "verify_certs": verify_certs,
                        "ssl_show_warn": False,
                        "ca_certs": None,
                        "ssl_assert_hostname": False,
                        "ssl_assert_fingerprint": None,
                    }
                )
            elasticsearch_client = Elasticsearch(**config)

            # Add more detailed logging
            logger.debug(f"Attempting to ping Elasticsearch at attempt {attempt + 1}")
            ping_result = elasticsearch_client.ping()
            if not ping_result:
                raise es_exceptions.ConnectionError("Failed to ping Elasticsearch")

            logger.info("Successfully connected to Elasticsearch")
            return elasticsearch_client

        except es_exceptions.ConnectionError as e:
            logger.error(
                f"Attempt {attempt + 1}/{max_retries}: Elasticsearch connection failed with error: {e}. Retrying in {retry_delay} seconds..."
            )
            logger.error(
                f"Connection details - Host: {host}, Port: {port}"
                + (f", Username: {username}" if use_auth else "")
            )
            if hasattr(e, "info"):
                logger.error(f"Error info: {e.info}")
            time.sleep(retry_delay)


class VectorStore:
    """
    A class to manage vector storage and search in Elasticsearch.

    This class provides functionality to create an index, add embeddings,
    and perform similarity searches using Elasticsearch.
    """

    def __init__(
        self,
        client: Elasticsearch,
        embeddings_providers: dict[str, EmbeddingModel],
        dims: int,
    ):
        """
        Initialize the VectorStore.

        Args:
            client: Pre-configured Elasticsearch client
            embeddings_providers: The models used to generate embeddings
            dims: The dimensionality of the embeddings
        """
        self.client = client
        self.embeddings_providers = embeddings_providers
        self.dims = dims

    @staticmethod
    def create_index_with_retries(
        client: Elasticsearch,
        index_name: str,
        retries: int = 5,
        delay: int = 10,
        dims: int = 1024,
    ) -> None:
        """
        Attempt to create the Elasticsearch index with multiple retries.

        Args:
            client: Elasticsearch client instance
            index_name: Name of the index to create
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            dims: Dimensionality of the embeddings
        """
        for attempt in range(retries):
            try:
                VectorStore.create_index(client, index_name, dims)
                return
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to create index failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        raise Exception("Failed to create index after several attempts")

    @staticmethod
    def create_index(client: Elasticsearch, index_name: str, dims: int = 1024) -> None:
        """
        Create the Elasticsearch index with appropriate settings and mappings.
        """
        if not client.indices.exists(index=index_name):
            client.indices.create(
                index=index_name,
                body={
                    "settings": {
                        "index": {"number_of_shards": 1, "number_of_replicas": 1},
                        "analysis": {"analyzer": {"default": {"type": "standard"}}},
                    },
                    "mappings": {
                        "properties": {
                            "embedding": {
                                "type": "dense_vector",
                                "dims": dims,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "metadata": {
                                "properties": {
                                    "contextualized_segment_text": {"type": "text"},
                                    "section_title": {"type": "text"},
                                    "pages": {"type": "integer"},
                                    "page_images": {
                                        "type": "keyword",
                                        "index": False,
                                        "doc_values": False,
                                    },
                                    "file_url": {"type": "keyword"},
                                    "title": {"type": "text"},
                                    "section_text": {"type": "text"},
                                    "index_name": {"type": "text"},
                                    "associated_organization_index_name": {
                                        "type": "keyword"
                                    },
                                    "nominal_creator_name": {"type": "keyword"},
                                    "filter_dimensions": {
                                        "type": "nested",
                                        "properties": {
                                            "dimension_name": {"type": "keyword"},
                                            "values": {"type": "keyword"},
                                        },
                                    },
                                    "visibility": {"type": "keyword"},
                                }
                            },
                        }
                    },
                },
            )
            logger.info(f"Index {index_name} created successfully.")
        else:
            logger.info(f"Index {index_name} already exists.")

    @staticmethod
    def delete_index(client: Elasticsearch, index_name: str, dims: int = 1536) -> None:
        """Delete the Elasticsearch index if it exists."""
        if client.indices.exists(index=index_name):
            client.indices.delete(
                index=index_name,
            )
            logger.info(f"Index {index_name} deleted successfully.")
        else:
            logger.info(f"Index {index_name} doesn't exist.")

    def add_embeddings_bulk(
        self, documents: list[dict[str, Any]], index_name: str
    ) -> None:
        """
        Add multiple embeddings in bulk for better performance.

        Args:
            documents: list of documents, each containing an embedding and metadata
            index_name: Name of the index to add documents to
        """
        try:
            actions = []
            for doc in documents:
                # Validate embedding
                embedding = doc.get("embedding")
                if not embedding or len(embedding) != self.dims:
                    logger.error(
                        f"Invalid embedding for document: {doc.get('metadata', {})}"
                    )
                    continue

                # Process filter dimensions
                metadata = doc.get("metadata", {})
                if "filter_dimensions" in metadata:
                    metadata["filter_dimensions"] = [
                        {
                            "dimension_name": dim_name,
                            "values": dim_values
                            if isinstance(dim_values, list)
                            else [dim_values],
                        }
                        for dim_name, dim_values in metadata[
                            "filter_dimensions"
                        ].items()
                    ]

                # Create bulk action
                action = {
                    "_index": index_name,
                    "_source": {"embedding": embedding, "metadata": metadata},
                }
                actions.append(action)

            if actions:
                success, failed = bulk(self.client, actions, refresh=True)
                logger.info(
                    f"Bulk indexing completed. Success: {success}, Failed: {failed}"
                )
            else:
                logger.warning("No valid documents to index")

        except Exception as e:
            error_message, _ = log_error(e, f"Error in bulk indexing to {index_name}")
            logger.error(error_message)
            raise

    def add_embedding(
        self, embedding: list[float], metadata: dict, index_name: Optional[str] = None
    ) -> None:
        """
        Add an embedding and its metadata to the index.

        Args:
            embedding: The vector embedding to be added
            metadata: Associated metadata for the embedding
            index_name: Optional override for the index name
        """
        try:
            # Use the provided index_name or fallback to the instance's index_name
            if index_name is None:
                index_name = self.index_name

            # Ensure the embedding is a list of floats
            if isinstance(embedding, dict) and "data" in embedding:
                embedding = embedding["data"][0]["embedding"]

            logger.debug(f"Embedding before adding to index {index_name}: {embedding}")

            if len(embedding) != self.dims:
                raise ValueError(
                    f"Embedding dimension mismatch. Expected {self.dims}, got {len(embedding)}"
                )

            if not all(isinstance(x, (float, int)) for x in embedding):
                raise ValueError("Embedding contains non-float values")

            logger.info(f"Metadata: {metadata['title']} {metadata['pages']}")
            # Convert filter_dimensions to nested format
            if "filter_dimensions" in metadata:
                nested_filter_dimensions = [
                    {
                        "dimension_name": dim_name,
                        "values": (
                            dim_values if isinstance(dim_values, list) else [dim_values]
                        ),
                    }
                    for dim_name, dim_values in metadata["filter_dimensions"].items()
                ]
                metadata["filter_dimensions"] = nested_filter_dimensions
            else:
                logger.warning(
                    "filter_dimensions not found in metadata. Creating an empty list."
                )
                metadata["filter_dimensions"] = []

            logger.info(f"Adding embedding to index {index_name} for: {metadata}")
            self.client.index(
                index=index_name,
                document={"embedding": embedding, "metadata": metadata},
            )
            logger.info(
                f"Successfully added embedding for: {metadata.copy().pop("page_images")} to index {index_name}"
            )

        except Exception as e:
            logger.error(
                f"Error adding embedding to Elasticsearch index {index_name}: {e}"
            )
            log_error(e, f"Error adding embedding to Elasticsearch index {index_name}")
            raise

    def construct_filter_query(
        self,
        filter_dimensions: Optional[dict[str, Union[str, list[str]]]] = None,
        visibility: Optional[str] = None,
        document_titles: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Construct the filter query based on filters and document titles.

        Args:
            filter_dimensions: Optional dictionary of filter dimensions to filter by
            visibility: Optional visibility filter ('public' or 'private')
            document_titles: Optional list of document titles for exact matching

        Returns:
            list[dict]: The constructed filter query for Elasticsearch
        """
        filter_query = []

        # Add titles filter if provided
        if document_titles:  # Check if document_titles is not None and not empty
            if len(document_titles) == 1:
                filter_query.append({"match": {"metadata.title": document_titles[0]}})
            else:
                filter_query.append(
                    {
                        "bool": {
                            "should": [
                                {"match": {"metadata.title": title}}
                                for title in document_titles
                            ]
                        }
                    }
                )

        # Add dimension filters if provided
        if filter_dimensions:
            nested_queries = []
            for dim_name, dim_values in filter_dimensions.items():
                logger.info(f"Filtering by {dim_name}: {dim_values}")
                if not isinstance(dim_values, list):
                    dim_values = [dim_values]

                nested_queries.append(
                    {
                        "nested": {
                            "path": "metadata.filter_dimensions",
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "term": {
                                                "metadata.filter_dimensions.dimension_name": dim_name
                                            }
                                        },
                                        {
                                            "terms": {
                                                "metadata.filter_dimensions.values": dim_values
                                            }
                                        },
                                    ]
                                }
                            },
                        }
                    }
                )

            if nested_queries:
                filter_query.append({"bool": {"must": nested_queries}})

        if visibility:
            filter_query.append({"term": {"metadata.visibility": visibility}})

        logger.debug(f"Constructed filter query: {filter_query}")
        return filter_query

    def vector_search(
        self,
        query_vector: list[float],
        index_names: Optional[Union[str, list[str]]] = None,
        filter_dimensions: Optional[dict] = None,
        visibility: Optional[str] = None,
        document_titles: Optional[list[str]] = None,
        size: int = 10,
    ) -> list[dict]:
        """
        Perform a similarity search with optional multi-document filtering.

        Args:
            query_vector: The query vector to search against
            index_names: The index(es) to search in
            filter_dimensions: Optional dictionary of filter dimensions
            visibility: Optional visibility filter
            document_titles: Optional list of document titles to filter by
            size: Number of results to return

        Returns:
            list[dict]: A list of search hits from Elasticsearch, filtered by the
                    specified document titles if provided
        """
        if index_names is None:
            index_names = [self.index_name]
        elif isinstance(index_names, str):
            index_names = [index_names]

        logger.info(f"Starting vector search in indices: {index_names}")
        if document_titles:
            logger.info(f"Filtering for documents: {document_titles}")

        # Construct the filter query with document titles
        filter_query = self.construct_filter_query(
            filter_dimensions, visibility, document_titles
        )

        # Construct the full query
        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_vector},
                            },
                        }
                    },
                    "filter": filter_query,
                }
            },
        }

        results = []
        for index_name in index_names:
            try:
                logger.info(f"Searching in index: {index_name}")
                response = self.client.search(index=index_name, body=body)
                hits = response.get("hits", {}).get("hits", [])
                if len(hits) == 0:
                    logger.warning(f"No hits returned for index: {index_name}")
                else:
                    results.extend(hits)
            except Exception as e:
                logger.error(f"Error searching index {index_name}: {e}")
                log_error(e, f"Error searching index {index_name}")

        logger.info(f"Total results returned: {len(results)}")
        return results

    def bm25_search(
        self,
        query: str,
        index_names: Optional[Union[str, list[str]]] = None,
        filter_dimensions: Optional[dict] = None,
        visibility: Optional[str] = None,
        document_titles: Optional[list[str]] = None,
        size: int = 10,
    ) -> list[dict]:
        """
        Perform a BM25 search with optional multi-document filtering.

        Args:
            query: The text query to search against
            index_names: The index(es) to search in
            filter_dimensions: Optional dictionary of filter dimensions
            visibility: Optional visibility filter
            document_titles: Optional list of document titles to filter by
            size: Number of results to return

        Returns:
            list[dict]: A list of search hits from Elasticsearch, filtered by the
                    specified document titles if provided
        """
        if index_names is None:
            index_names = [self.index_name]
        elif isinstance(index_names, str):
            index_names = [index_names]

        logger.info(f"Starting BM25 search in indices: {index_names}")
        if document_titles:
            logger.info(f"Filtering for documents: {document_titles}")

        # Construct the filter query with document titles
        filter_query = self.construct_filter_query(
            filter_dimensions, visibility, document_titles
        )

        # Construct the full query
        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "metadata.contextualized_segment_text",
                                "metadata.section_title",
                                "metadata.title",
                                "metadata.section_text",
                            ],
                        }
                    },
                    "filter": filter_query,
                }
            },
        }

        results = []
        for index_name in index_names:
            try:
                logger.info(f"Searching in index: {index_name}")
                response = self.client.search(index=index_name, body=body)
                hits = response.get("hits", {}).get("hits", [])
                if len(hits) == 0:
                    logger.warning(f"No hits returned for index: {index_name}")
                else:
                    results.extend(hits)
            except Exception as e:
                logger.error(f"Error searching index {index_name}: {e}")
                log_error(e, f"Error searching index {index_name}")

        logger.info(f"Total results returned: {len(results)}")
        return results

    def combine_results_rrf(
        self, vector_results: list[dict], bm25_results: list[dict], k: int = 60
    ) -> list[dict]:
        """
        Combine vector search and BM25 search results using Reciprocal Rank Fusion.

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            k: Constant to prevent division by zero and reduce the impact of high rankings

        Returns:
            Combined and re-ranked results
        """
        combined_scores = {}
        all_results = {}

        # Process vector search results and BM25 search results
        for rank, result in enumerate(vector_results + bm25_results):
            doc_id = result["_id"]
            score = 1 / (rank + k)
            combined_scores[doc_id] = combined_scores.get(doc_id, 0) + score
            all_results[doc_id] = result

        # Sort the results by their combined scores
        sorted_results = sorted(
            combined_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Create the final results list
        final_results = [
            {**all_results[doc_id], "_score": score} for doc_id, score in sorted_results
        ]

        return final_results

    def as_retriever(self) -> "VectorStore":
        """
        Return self as a retriever object.

        Returns:
            The current instance
        """
        return self

    def get_relevant_documents(
        self,
        query: str,
        index_names: Optional[Union[str, list[str]]] = None,
        filter_dimensions: Optional[dict] = None,
        visibility: Optional[str] = None,
        document_titles: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Retrieve relevant documents based on a text query with additional metadata filtering.

        Args:
            query: The text query to search for
            index_names: The index(es) to search in
            filter_dimensions: dictionary of filter dimensions to filter by
            visibility: The visibility to filter by
            document_titles: list of documents to filter by

        Returns:
            A list of relevant documents with their metadata and similarity scores
        """
        try:
            query_embedding = (
                self.embeddings_providers["cohere"]
                .embed(query, input_type="search_query", model_id="embed-english-v3.0")
                .embeddings[0]
            )
            logger.info(f"Query embedding: {query_embedding}")

            # Use the provided index_names or fallback to the instance's index_name
            logger.info(f"index_names is {index_names}")
            if index_names is None:
                index_names = [self.index_name]
            elif isinstance(index_names, str):
                index_names = [index_names]

            # Perform vector search
            vector_results = self.vector_search(
                query_embedding,
                index_names,
                filter_dimensions,
                visibility,
                document_titles,
            )

            # Perform BM25 search
            bm25_results = self.bm25_search(
                query, index_names, filter_dimensions, visibility, document_titles
            )

            # Combine results using RRF
            combined_results = self.combine_results_rrf(vector_results, bm25_results)

            if not combined_results:
                logger.warning("No relevant documents found.")
                return []

            documents = []
            for result in combined_results:
                document = {
                    "metadata": result["_source"]["metadata"],
                    "similarity": result["_score"],
                }
                document["contextualized_segment_text"] = result["_source"][
                    "metadata"
                ].get("contextualized_segment_text", "")

                # Log the entire document
                logger.debug(f"Retrieved document: {result}")

                documents.append(document)
            logger.debug([document["similarity"] for document in documents])

            return documents
        except ConnectError:
            error_message, stack_trace = log_error(
                ConnectError(),
                "Internal server error. Could not reach the document embedding endpoint.",
            )
            logger.error(error_message)
            return []
        except Exception as e:
            error_message, stack_trace = log_error(
                e, "Error retrieving relevant documents"
            )
            logger.error(error_message)
            return []
