import pytest
from elasticsearch import Elasticsearch
from app.app import create_app


@pytest.mark.integration
class TestSearchIntegration:
    @pytest.fixture
    def app(self):
        """Create test app with container configuration"""
        app = create_app()
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture(autouse=True)
    def setup_test_index(self, app):
        """Setup and teardown test index"""
        es = Elasticsearch(
            f"http://{app.config['ELASTICSEARCH_HOST']}:{app.config['ELASTICSEARCH_PORT']}"
        )
        test_index = "test_search_index"

        # Create test index
        es.indices.create(index=test_index, ignore=400)
        es.index(index=test_index, document={"content": "test document"}, refresh=True)

        yield

        # Cleanup
        es.indices.delete(index=test_index, ignore=[404])

    def test_search_endpoint(self, client):
        """Test search endpoint with containerized ES"""
        # Arrange
        search_query = {"query": "test"}

        # Act
        response = client.post("/api/search", json=search_query)

        # Assert
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) > 0
