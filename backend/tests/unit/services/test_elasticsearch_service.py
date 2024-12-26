import pytest
from unittest.mock import Mock, patch
from elasticsearch import exceptions as es_exceptions

from services.elasticsearch_service import (
    create_elasticsearch_client_with_retries,
    VectorStore,
)


@pytest.mark.unit
class TestElasticsearchClientCreation:
    """Test suite for Elasticsearch client creation functionality"""

    @patch(
        "services.elasticsearch_service.Elasticsearch"
    )  # Patch where the client is actually used
    def test_client_creation_success(self, mock_es_class):
        """Test successful creation of Elasticsearch client"""
        print("Starting test")  # Debug print

        # Configure the mock instance that will be returned
        mock_es_instance = Mock()
        mock_es_instance.ping.return_value = True
        mock_es_class.return_value = mock_es_instance

        print("About to create client")  # Debug print
        client = create_elasticsearch_client_with_retries(
            host="test-host",
            port=9200,
            username="test-user",
            password="test-pass",
        )
        print("Client created")  # Debug print

        # Verify the results
        mock_es_class.assert_called_once()
        mock_es_instance.ping.assert_called_once()
        assert client == mock_es_instance

    @patch("services.elasticsearch_service.Elasticsearch")
    @patch("time.sleep")  # Mock sleep to avoid delays
    def test_client_creation_retry_on_failure(self, mock_sleep, mock_es_class):
        """Test client creation retries on connection failure"""
        print("Starting retry test")  # Debug print

        # Configure the mock instance
        mock_es_instance = Mock()
        mock_es_instance.ping.side_effect = [
            es_exceptions.ConnectionError("Test error"),
            es_exceptions.ConnectionError("Test error"),
            True,
        ]
        mock_es_class.return_value = mock_es_instance

        print("About to create client with retries")  # Debug print
        client = create_elasticsearch_client_with_retries(
            host="test-host",
            port=9200,
            username="test-user",
            password="test-pass",
            max_retries=3,
            retry_delay=0,
        )
        print("Client created")  # Debug print

        # Verify the results
        assert mock_es_instance.ping.call_count == 3
        assert client == mock_es_instance
        mock_sleep.assert_called()


@pytest.mark.unit
class TestVectorStore:
    """Test suite for VectorStore functionality"""

    @pytest.fixture
    def vector_store(self, mock_es_client, mock_embedding_model):
        """Create VectorStore instance with mocked dependencies"""
        return VectorStore(
            client=mock_es_client, embedding_model=mock_embedding_model, dims=3
        )

    def test_create_index(self, mock_es_client):
        """Test index creation"""
        # Test when index doesn't exist
        mock_es_client.indices.exists.return_value = False
        VectorStore.create_index(mock_es_client, "test_index", dims=3)

        mock_es_client.indices.create.assert_called_once()
        create_args = mock_es_client.indices.create.call_args[1]
        assert create_args["index"] == "test_index"
        assert (
            "dense_vector"
            in create_args["body"]["mappings"]["properties"]["embedding"]["type"]
        )

        # Test when index already exists
        mock_es_client.reset_mock()
        mock_es_client.indices.exists.return_value = True
        VectorStore.create_index(mock_es_client, "test_index", dims=3)
        mock_es_client.indices.create.assert_not_called()

    def test_create_index_with_retries(self, mock_es_client):
        """Test index creation with retry logic"""
        mock_es_client.indices.exists.return_value = False
        mock_es_client.indices.create.side_effect = [
            es_exceptions.ConnectionError("Test error"),
            es_exceptions.ConnectionError("Test error"),
            {"acknowledged": True},
        ]

        with patch("time.sleep"):
            VectorStore.create_index_with_retries(
                mock_es_client, "test_index", retries=3, delay=0, dims=3
            )

        assert mock_es_client.indices.create.call_count == 3

    def test_add_embedding(self, vector_store, mock_es_client):
        """Test adding a single embedding"""
        embedding = [0.1, 0.2, 0.3]
        metadata = {
            "title": "test doc",
            "filter_dimensions": {"category": "test"},
        }

        vector_store.add_embedding(embedding, metadata, "test_index")

        mock_es_client.index.assert_called_once()
        index_args = mock_es_client.index.call_args[1]
        assert index_args["index"] == "test_index"
        assert index_args["document"]["embedding"] == embedding
        assert isinstance(index_args["document"]["metadata"]["filter_dimensions"], list)

    def test_add_embeddings_bulk(self, vector_store, mock_es_client):
        """Test bulk embedding addition"""
        documents = [
            {
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {
                    "title": "doc1",
                    "filter_dimensions": {"category": "test1"},
                },
            },
            {
                "embedding": [0.4, 0.5, 0.6],
                "metadata": {
                    "title": "doc2",
                    "filter_dimensions": {"category": "test2"},
                },
            },
        ]

        # Mock the elasticsearch.helpers.bulk function instead of client.bulk
        with patch(
            "services.elasticsearch_service.bulk", return_value=(2, [])
        ) as mock_bulk:
            vector_store.add_embeddings_bulk(documents, "test_index")

            # Verify bulk was called with correct arguments
            mock_bulk.assert_called_once()

            # Verify the actions passed to bulk
            call_args = mock_bulk.call_args
            assert call_args[0][0] == mock_es_client  # First arg should be the client
            actions = call_args[0][1]  # Second arg should be the actions list
            assert len(actions) == 2  # Should have 2 documents

            # Verify the structure of the actions
            for action in actions:
                assert action["_index"] == "test_index"
                assert "embedding" in action["_source"]
                assert "metadata" in action["_source"]
                assert isinstance(
                    action["_source"]["metadata"]["filter_dimensions"], list
                )

    def test_vector_search(
        self, vector_store, mock_es_client, vector_store_mock_responses
    ):
        """Test vector search functionality"""
        mock_es_client.search.return_value = vector_store_mock_responses[
            "vector_search"
        ]

        query_vector = [0.1, 0.2, 0.3]
        filter_dimensions = {"category": "test_category"}

        results = vector_store.vector_search(
            query_vector=query_vector,
            index_names=["test_index"],
            filter_dimensions=filter_dimensions,
            size=10,
        )

        assert len(results) == 1
        assert results[0]["_source"]["metadata"]["title"] == "test doc"
        mock_es_client.search.assert_called_once()

    def test_bm25_search(
        self, vector_store, mock_es_client, vector_store_mock_responses
    ):
        """Test BM25 search functionality"""
        mock_es_client.search.return_value = vector_store_mock_responses["bm25_search"]

        results = vector_store.bm25_search(
            query="test query", index_names=["test_index"], size=10
        )

        assert len(results) == 1
        assert results[0]["_source"]["metadata"]["title"] == "test doc"
        mock_es_client.search.assert_called_once()

    def test_get_relevant_documents(
        self, vector_store, mock_es_client, vector_store_mock_responses
    ):
        """Test document retrieval with combined search"""
        # Mock vector search results
        mock_es_client.search.side_effect = [
            vector_store_mock_responses["vector_search"],
            vector_store_mock_responses["bm25_search"],
        ]

        documents = vector_store.get_relevant_documents(
            query="test query",
            index_names=["test_index"],
            filter_dimensions={"category": "test_category"},
        )

        assert len(documents) > 0
        assert "metadata" in documents[0]
        assert "similarity" in documents[0]
        assert mock_es_client.search.call_count == 2

    def test_construct_filter_query(self, vector_store):
        """Test filter query construction"""
        filter_dimensions = {"category": ["test1", "test2"]}
        visibility = "public"
        document_titles = ["doc1", "doc2"]

        filter_query = vector_store.construct_filter_query(
            filter_dimensions=filter_dimensions,
            visibility=visibility,
            document_titles=document_titles,
        )

        assert (
            len(filter_query) == 3
        )  # Should have title, dimension, and visibility filters
        assert any("metadata.visibility" in str(q) for q in filter_query)
        assert any("metadata.title" in str(q) for q in filter_query)
        assert any("metadata.filter_dimensions" in str(q) for q in filter_query)

    def test_combine_results_rrf(self, vector_store, mock_es_client):
        """Test Reciprocal Rank Fusion of search results"""
        vector_results = [
            {
                "_id": "1",
                "_score": 0.8,
                "_source": {
                    "metadata": {
                        "title": "doc1",
                        "filter_dimensions": [
                            {"dimension_name": "category", "values": ["test1"]}
                        ],
                    }
                },
            },
            {
                "_id": "2",
                "_score": 0.6,
                "_source": {
                    "metadata": {
                        "title": "doc2",
                        "filter_dimensions": [
                            {"dimension_name": "category", "values": ["test2"]}
                        ],
                    }
                },
            },
        ]

        bm25_results = [
            {
                "_id": "2",
                "_score": 0.9,
                "_source": {
                    "metadata": {
                        "title": "doc2",
                        "filter_dimensions": [
                            {"dimension_name": "category", "values": ["test2"]}
                        ],
                    }
                },
            },
            {
                "_id": "3",
                "_score": 0.7,
                "_source": {
                    "metadata": {
                        "title": "doc3",
                        "filter_dimensions": [
                            {"dimension_name": "category", "values": ["test3"]}
                        ],
                    }
                },
            },
        ]

        combined = vector_store.combine_results_rrf(vector_results, bm25_results)

        # Basic structural checks
        assert len(combined) == 3, "Should have 3 unique documents"

        # Verify document order
        assert (
            combined[0]["_id"] == "2"
        ), "Doc2 should be ranked first (appears in both results)"

        # Verify all documents are present
        result_ids = {doc["_id"] for doc in combined}
        assert result_ids == {"1", "2", "3"}, "All document IDs should be present"

        # Verify relative scoring
        doc2_score = next(doc["_score"] for doc in combined if doc["_id"] == "2")
        doc1_score = next(doc["_score"] for doc in combined if doc["_id"] == "1")
        doc3_score = next(doc["_score"] for doc in combined if doc["_id"] == "3")

        assert doc2_score > doc1_score, "Doc2 should have higher score than Doc1"
        assert doc2_score > doc3_score, "Doc2 should have higher score than Doc3"
