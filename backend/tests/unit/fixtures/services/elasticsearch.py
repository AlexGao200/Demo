import uuid
import os
import pytest
from unittest.mock import MagicMock
from services.elasticsearch_service import VectorStore


def get_test_es_index() -> str:
    """
    Generate a unique Elasticsearch index name for parallel testing.
    Incorporates worker ID when running with pytest-xdist.

    Returns:
        str: Unique test index name
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "")
    base_index = uuid.uuid4()
    if worker_id:
        return f"{base_index}_{worker_id}"
    return str(base_index)


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model for testing VectorStore"""
    mock = MagicMock()
    mock.embed.return_value = [[0.1, 0.2, 0.3]]  # Simple 3D vector for testing
    return mock


@pytest.fixture
def vector_store(mock_es_client, mock_embedding_model):
    """Create VectorStore instance with mocked dependencies"""
    return VectorStore(
        client=mock_es_client, embedding_model=mock_embedding_model, dims=3
    )


@pytest.fixture
def vector_store_mock_responses():
    """Provide standard mock responses for VectorStore operations"""
    return {
        "vector_search": {
            "hits": {
                "hits": [
                    {
                        "_id": "1",
                        "_score": 0.8,
                        "_source": {
                            "embedding": [0.1, 0.2, 0.3],
                            "metadata": {
                                "contextualized_segment_text": "test text",
                                "title": "test doc",
                                "filter_dimensions": [
                                    {
                                        "dimension_name": "category",
                                        "values": ["test_category"],
                                    }
                                ],
                            },
                        },
                    }
                ]
            }
        },
        "bm25_search": {
            "hits": {
                "hits": [
                    {
                        "_id": "2",
                        "_score": 0.9,
                        "_source": {
                            "metadata": {
                                "contextualized_segment_text": "test text",
                                "title": "test doc",
                            }
                        },
                    }
                ]
            }
        },
    }


@pytest.fixture
def mock_index_service(mocker):
    """Create a mock index service for testing"""
    mock = mocker.Mock()

    def create_organization_index(*args, **kwargs):
        index_name = f"test_index_{uuid.uuid4().hex[:8]}"
        print("\nMock create_organization_index called")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")
        print(f"Returning index name: {index_name}")
        return index_name

    mock.create_organization_index = mocker.Mock(side_effect=create_organization_index)
    return mock


@pytest.fixture
def mock_es_client(monkeypatch) -> MagicMock:
    """
    Mock Elasticsearch client for tests that don't need real ES.
    Mocks common ES operations and provides default responses.
    """
    # Create the mock client with all necessary attributes
    es_mock = MagicMock()

    # Set up default returns for common operations
    es_mock.indices.put_mapping.return_value = {"acknowledged": True}
    es_mock.indices.create.return_value = {"acknowledged": True}
    es_mock.indices.exists.return_value = False
    es_mock.indices.delete.return_value = {"acknowledged": True}
    es_mock.ping.return_value = True
    es_mock.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}
    es_mock.bulk.return_value = {"errors": False, "items": []}

    # Important: Reset all mock calls after each test
    es_mock.reset_mock()

    # Create a factory function that returns a fresh mock for each test
    def mock_es_factory(*args, **kwargs):
        new_mock = MagicMock()
        # Copy all the return values and side effects from the template mock
        new_mock.indices = MagicMock()
        new_mock.indices.put_mapping.return_value = (
            es_mock.indices.put_mapping.return_value
        )
        new_mock.indices.create.return_value = es_mock.indices.create.return_value
        new_mock.indices.exists.return_value = es_mock.indices.exists.return_value
        new_mock.indices.delete.return_value = es_mock.indices.delete.return_value
        new_mock.ping.return_value = es_mock.ping.return_value
        new_mock.search.return_value = es_mock.search.return_value
        new_mock.bulk.return_value = es_mock.bulk.return_value
        return new_mock

    # Patch both the Elasticsearch class and the client creation function
    monkeypatch.setattr("elasticsearch.Elasticsearch", mock_es_factory)
    monkeypatch.setattr(
        "services.elasticsearch_service.create_elasticsearch_client_with_retries",
        mock_es_factory,
    )

    return es_mock


@pytest.fixture
def es_test_index() -> str:
    """
    Fixture to provide a unique test index name.
    Useful for tests that need to reference a specific index name.

    Returns:
        str: Unique test index name
    """
    return get_test_es_index()


@pytest.fixture
def es_bulk_success_response() -> dict:
    """
    Fixture providing a standard successful bulk operation response.
    Useful for mocking bulk operations in tests.

    Returns:
        dict: Mock bulk operation success response
    """
    return {
        "took": 30,
        "errors": False,
        "items": [
            {
                "index": {
                    "_index": "test_index",
                    "_id": str(uuid.uuid4()),
                    "_version": 1,
                    "result": "created",
                    "status": 201,
                }
            }
        ],
    }


@pytest.fixture
def es_search_response() -> dict:
    """
    Fixture providing a standard search response.
    Useful for mocking search operations in tests.

    Returns:
        dict: Mock search response
    """
    return {
        "took": 5,
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "max_score": 1.0,
            "hits": [
                {
                    "_index": "test_index",
                    "_id": str(uuid.uuid4()),
                    "_score": 1.0,
                    "_source": {"test_field": "test_value"},
                }
            ],
        },
    }


def configure_es_mock_responses(mock_client: MagicMock, **kwargs) -> None:
    """
    Configure custom responses for ES mock client.
    Allows tests to easily customize mock behavior.

    Args:
        mock_client: The mock ES client to configure
        **kwargs: Custom responses for different operations
    """
    default_responses = {
        "indices.exists": False,
        "indices.create": {"acknowledged": True},
        "indices.delete": {"acknowledged": True},
        "indices.put_mapping": {"acknowledged": True},
        "search": {"hits": {"hits": [], "total": {"value": 0}}},
        "bulk": {"errors": False, "items": []},
    }

    responses = {**default_responses, **kwargs}

    for operation, response in responses.items():
        parts = operation.split(".")
        if len(parts) == 2:
            getattr(getattr(mock_client, parts[0]), parts[1]).return_value = response
        else:
            getattr(mock_client, operation).return_value = response


# Export all needed items
__all__ = [
    "get_test_es_index",
    "mock_es_client",
    "es_test_index",
    "es_bulk_success_response",
    "es_search_response",
    "configure_es_mock_responses",
    "mock_embedding_model",
    "vector_store_mock_responses",
]
