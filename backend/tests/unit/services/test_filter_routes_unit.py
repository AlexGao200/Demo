import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from models.index_registry import IndexRegistry, FilterDimension
from models.file_metadata import FileMetadata
from models.user_organization import UserOrganization
from loguru import logger
from bson import ObjectId
import uuid


@pytest.mark.blueprints(["filter"])
class TestFilterRoutes:
    @pytest.fixture(autouse=True)
    def mock_es_client(self, monkeypatch):
        """Mock Elasticsearch client for all tests"""
        es_mock = MagicMock()
        es_mock.indices.put_mapping.return_value = {"acknowledged": True}

        # Mock client creation function everywhere it might be called
        def mock_es_factory(*args, **kwargs):
            return es_mock

        monkeypatch.setattr(
            "services.elasticsearch_service.create_elasticsearch_client_with_retries",
            mock_es_factory,
        )
        monkeypatch.setattr(
            "blueprints.filter_routes.create_elasticsearch_client_with_retries",
            mock_es_factory,
        )

        return es_mock

    @pytest.fixture
    def filter_app(self, minimal_app, mock_es_client):
        """Configure minimal app with filter blueprint"""
        from blueprints.filter_routes import create_filter_blueprint

        minimal_app.config["ELASTICSEARCH_HOST"] = "localhost"
        minimal_app.config["ELASTICSEARCH_PORT"] = 9200

        # Create and register the filter blueprint
        filter_bp = create_filter_blueprint()
        minimal_app.register_blueprint(filter_bp)
        return minimal_app

    @pytest.fixture
    def filter_client(self, filter_app):
        return filter_app.test_client()

    @pytest.fixture
    def test_filter_dimension(self):
        """Create a test filter dimension"""
        dimension = FilterDimension(
            name="test_dimension", values=["value1", "value2", "value3"]
        ).save()
        yield dimension
        dimension.delete()

    @pytest.fixture
    def test_index_with_filters(self, test_filter_dimension, test_organization):
        """Create a test index registry with filter dimensions"""
        index = IndexRegistry(
            index_name=test_organization.index_name,
            filter_dimensions=[test_filter_dimension],
            index_display_name=test_organization.name,
            entity_type="organization",
            entity_id=str(test_organization.id),
        ).save()
        yield index
        index.delete()

    def test_get_visibilities(
        self, filter_client, auth_headers, test_index_with_filters
    ):
        """Test visibility retrieval based on index types"""
        # Test with organization index
        response = filter_client.post(
            "/api/filter/get-visibilities",
            json={"indexNames": [test_index_with_filters.index_name]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert set(data["visibilities"]) == {"public", "private"}

        # Test with user index - need to create a mock user
        mock_user_id = str(ObjectId())  # Generate a mock user ID
        user_index = IndexRegistry(
            index_name="user_test",
            filter_dimensions=[],
            index_display_name="User Test",
            entity_type="user",
            entity_id=mock_user_id,
        ).save()

        try:
            response = filter_client.post(
                "/api/filter/get-visibilities",
                json={"indexNames": ["user_test"]},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["visibilities"] == ["private"]
        finally:
            user_index.delete()

    def test_get_filter_dimensions_pagination(
        self, filter_client, auth_headers, test_index_with_filters
    ):
        """Test paginated retrieval of filter dimensions"""
        response = filter_client.get(
            f"/api/filter/get-filter-dimensions?index_names[]={test_index_with_filters.index_name}&page=1&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["filter_dimensions"]) > 0
        assert data["total_filters"] == len(test_index_with_filters.filter_dimensions)
        assert "page" in data
        assert "limit" in data

    def test_create_filter_dimension(
        self, filter_client, auth_headers, test_user, test_organization, mock_es_client
    ):
        """Test creation of new filter dimension"""
        # Create user organization with required index_name first
        UserOrganization(
            user=test_user,
            organization=test_organization,
            role="admin",
            is_active=True,
            index_name=test_organization.index_name,
        ).save()

        # Create initial index registry
        registry = IndexRegistry(
            index_name=test_organization.index_name,
            filter_dimensions=[],
            index_display_name=test_organization.name,
            entity_type="organization",
            entity_id=str(test_organization.id),
        ).save()

        try:
            with filter_client.application.app_context():
                response = filter_client.post(
                    "/api/filter/create-filter-dimension",
                    json={
                        "dimension_name": "new_dimension",
                        "index_names": [test_organization.index_name],
                    },
                    headers=auth_headers,
                )

                print(
                    f"Response Data: {response.get_data(as_text=True)}"
                )  # Debug print

                assert response.status_code == 201
                data = response.get_json()
                assert "dimension_id" in data
                assert data["dimension_name"] == "new_dimension"

                # Verify ES mapping was updated
                mock_es_client.indices.put_mapping.assert_called_once_with(
                    index=test_organization.index_name,
                    body={
                        "properties": {
                            "filter_dimensions.new_dimension": {"type": "keyword"}
                        }
                    },
                )

                # Verify filter dimension was added to index registry
                updated_registry = IndexRegistry.objects.get(id=registry.id)
                assert any(
                    dim.name == "new_dimension"
                    for dim in updated_registry.filter_dimensions
                )
        finally:
            registry.delete()

    def test_add_value_to_filter_dimension(
        self, filter_client, auth_headers, test_filter_dimension
    ):
        """Test adding new value to existing filter dimension"""
        response = filter_client.post(
            "/api/filter/add-value-to-filter-dimension",
            json={"dimension_id": str(test_filter_dimension.id), "value": "new_value"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        updated_dimension = FilterDimension.objects.get(id=test_filter_dimension.id)
        assert "new_value" in updated_dimension.values

    def test_filter_documents(
        self,
        filter_client,
        auth_headers,
        test_user,
        test_organization,
        test_index_with_filters,
    ):
        """Test document filtering with multiple criteria"""
        logger.info("Starting test_filter_documents")

        # Create a filter dimension to use
        test_dimension = FilterDimension(
            name="test_dimension", values=["value1", "value2", "value3"]
        ).save()
        # After creating test_dimension
        print(f"Filter dimension structure: {test_dimension.to_json()}")

        # Update existing index registry with our new filter dimension
        test_index_with_filters.filter_dimensions.append(test_dimension)
        test_index_with_filters.save()
        logger.info(f"Updated index registry: {test_index_with_filters.to_json()}")

        # Verify index registry update
        updated_registry = IndexRegistry.objects.get(id=test_index_with_filters.id)
        logger.info(
            f"Verified index registry dimensions: {[str(d.id) for d in updated_registry.filter_dimensions]}"
        )

        # Create test documents with filter dimensions using the dimension ID
        doc1 = FileMetadata(
            name="test_doc_1.pdf",
            title="Test Doc 1",
            s3_url="https://test-bucket.s3.amazonaws.com/test1.pdf",
            document_hash="hash1",
            index_names=[test_organization.index_name],
            filter_dimensions={str(test_dimension.id): ["value1"]},
            visibility="public",
            organizations=[test_organization],
            originating_user=test_user,
            index_display_name="Test Index",
            nominal_creator_name="Test Org",
            created_at=datetime.now(timezone.utc),
        ).save()
        # After creating doc1
        print(
            f"Doc1 details: index_names={doc1.index_names}, filter_dimensions={doc1.filter_dimensions}, visibility={doc1.visibility}"
        )

        doc2 = FileMetadata(
            name="test_doc_2.pdf",
            title="Test Doc 2",
            s3_url="https://test-bucket.s3.amazonaws.com/test2.pdf",
            document_hash="hash2",
            index_names=[test_organization.index_name],
            filter_dimensions={str(test_dimension.id): ["value2"]},
            visibility="public",
            organizations=[test_organization],
            originating_user=test_user,
            index_display_name="Test Index",
            nominal_creator_name="Test Org",
            created_at=datetime.now(timezone.utc),
        ).save()
        logger.info(f"Created doc2 with filter dimensions: {doc2.filter_dimensions}")

        # Create a personal document in user's index
        personal_doc = FileMetadata(
            name="personal_doc.pdf",
            title="Personal Doc",
            s3_url="https://test-bucket.s3.amazonaws.com/personal.pdf",
            document_hash="hash3",
            index_names=[f"user_{test_user.id}"],
            filter_dimensions={},
            visibility="public",
            organizations=[],
            originating_user=test_user,
            index_display_name="Personal Index",
            nominal_creator_name="Personal Index",
            created_at=datetime.now(timezone.utc),
        ).save()
        logger.info(f"Created personal doc with index: {personal_doc.index_names}")

        try:
            # Create organization membership for private doc access
            org_membership = UserOrganization(
                user=test_user,
                organization=test_organization,
                role="member",
                is_active=True,
                index_name=test_organization.index_name,
            ).save()
            logger.info(f"Created organization membership: {org_membership.to_json()}")

            # Verify documents exist in database before filtering
            existing_docs = FileMetadata.objects(
                index_names=test_organization.index_name
            ).all()
            logger.info(f"Found {len(existing_docs)} documents in DB before filtering")
            for doc in existing_docs:
                logger.info(
                    f"Document: {doc.title}, Index: {doc.index_names}, Filters: {doc.filter_dimensions}"
                )

            # Test filtering with dimension values
            query_string = (
                f"indices[0][name]={test_organization.index_name}"
                f"&indices[0][display_name]=Test Index"
                f"&filterDimNames[]={str(test_dimension.id)}"
                f"&filterDimValues[0][0]=value1"
                f"&page=1"
                f"&sortField=title"
                f"&sortOrder=asc"
            )
            logger.info(f"Using query string: {query_string}")

            # Verify the query parameters
            logger.info(f"Organization index name: {test_organization.index_name}")
            logger.info(f"Dimension ID used in query: {test_dimension.id}")

            response = filter_client.get(
                f"/api/filter/filter_documents?{query_string}", headers=auth_headers
            )
            logger.info(f"Response status: {response.status_code}")

            # Get raw response data for debugging
            raw_response = response.get_data(as_text=True)
            logger.info(f"Raw response: {raw_response}")

            assert response.status_code == 200
            data = response.get_json()
            logger.info(f"Parsed response data: {data}")

            # Check documents that match our filter criteria directly in DB
            matching_docs = FileMetadata.objects(
                index_names=test_organization.index_name,
                **{f"filter_dimensions__{str(test_dimension.id)}": "value1"},
            ).all()
            logger.info(
                f"Direct DB query found {len(matching_docs)} matching documents"
            )
            for doc in matching_docs:
                logger.info(
                    f"Matching doc: {doc.title}, Filters: {doc.filter_dimensions}"
                )

            assert (
                len(data["documents"]) == 1
            ), f"Expected 1 document, got {len(data['documents'])}. Documents: {data['documents']}"
            assert data["documents"][0]["title"] == "Test Doc 1"

            # Test filtering with second value
            query_string = (
                f"indices[0][name]={test_organization.index_name}"
                f"&indices[0][display_name]=Test Index"
                f"&filterDimNames[]={str(test_dimension.id)}"
                f"&filterDimValues[0][0]=value2"
                f"&page=1"
                f"&sortField=title"
                f"&sortOrder=asc"
            )
            logger.info(f"Using second query string: {query_string}")

            response = filter_client.get(
                f"/api/filter/filter_documents?{query_string}", headers=auth_headers
            )
            logger.info(f"Second response status: {response.status_code}")

            assert response.status_code == 200
            data = response.get_json()
            logger.info(f"Second response data: {data}")

            assert len(data["documents"]) == 1
            assert data["documents"][0]["title"] == "Test Doc 2"

            # Test filtering personal documents
            query_string = (
                f"indices[0][name]=user_{test_user.id}"
                f"&indices[0][display_name]=Personal Index"
                f"&page=1"
                f"&sortField=title"
                f"&sortOrder=asc"
            )
            logger.info(f"Using personal docs query string: {query_string}")

            response = filter_client.get(
                f"/api/filter/filter_documents?{query_string}", headers=auth_headers
            )
            logger.info(f"Personal docs response status: {response.status_code}")

            assert response.status_code == 200
            data = response.get_json()
            logger.info(f"Personal docs response data: {data}")

            assert len(data["documents"]) == 1
            assert data["documents"][0]["title"] == "Personal Doc"

        finally:
            # Clean up test data
            logger.info("Cleaning up test data...")
            doc1.delete()
            doc2.delete()
            personal_doc.delete()
            test_dimension.delete()
            logger.info("Test data cleanup complete")

    def test_unauthorized_access(self, filter_client):
        """Test endpoints reject unauthorized access appropriately"""
        endpoints = [
            (
                "POST",
                "/api/filter/get-visibilities",
                {"Content-Type": "application/json"},
                {"indexNames": ["test"]},
            ),
            (
                "GET",
                "/api/filter/get-filter-dimensions",
                {"Content-Type": "application/json"},
                None,
            ),
            (
                "POST",
                "/api/filter/create-filter-dimension",
                {"Content-Type": "application/json"},
                {"dimension_name": "test", "index_names": ["test"]},
            ),
        ]

        # Test with no auth
        for method, endpoint, headers, data in endpoints:
            # Test completely unauthorized (no token)
            if data is not None:
                response = filter_client.open(
                    endpoint, method=method, headers=headers, json=data
                )
            else:
                response = filter_client.open(endpoint, method=method, headers=headers)
            assert (
                response.status_code == 401
            ), f"Expected 401 for {method} {endpoint}, got {response.status_code}"

            # Test with guest token
            guest_token = f"guest_{uuid.uuid4().hex}"
            headers_with_guest = {**headers, "Authorization": f"Bearer {guest_token}"}

            if data is not None:
                response = filter_client.open(
                    endpoint, method=method, headers=headers_with_guest, json=data
                )
            else:
                response = filter_client.open(
                    endpoint, method=method, headers=headers_with_guest
                )
            assert (
                response.status_code == 401
            ), f"Expected 401 for guest access to {method} {endpoint}, got {response.status_code}"
