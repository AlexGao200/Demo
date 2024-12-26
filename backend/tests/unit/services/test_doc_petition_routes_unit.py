import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from models.pending import PendingDocument
from models.organization import Organization
from io import BytesIO
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash
from bson import ObjectId
import uuid
import os


@pytest.mark.blueprints(["petition", "auth"])  # Include both blueprints
class TestPetitionRoutes:
    @pytest.fixture
    def mock_index_service(self):
        with patch("services.index_service.IndexService") as mock:
            mock.create_user_index.return_value = "test_index"
            mock.create_index_for_entity.return_value = "test_index"
            yield mock

    @pytest.fixture
    def mock_file_service(self):
        mock = MagicMock()

        async def mock_process(
            file_storage,
            title,
            index_name,
            visibility,
            originating_user,
            organizations,
            nominal_creator_name,
        ):
            return {
                "file_metadata": {
                    "id": "123",
                    "title": title,
                    "index_names": [index_name],
                },
                "index": index_name,
            }

        mock.process_upload = AsyncMock(side_effect=mock_process)
        return mock

    @pytest.fixture
    def mock_chat_pdf(self, mock_s3_service):
        mock = MagicMock()
        mock.s3_service = mock_s3_service
        return mock

    @pytest.fixture
    def mock_email_service(self):
        mock = MagicMock()
        mock.send.return_value = True
        return mock

    @pytest.fixture
    def petition_app(
        self,
        minimal_app,
        mock_s3_service,
        mock_file_service,
        mock_email_service,
        mock_guest_manager,
    ):
        """Configure minimal app with petition blueprint"""
        from blueprints.doc_petition_routes import create_petition_blueprint

        mock_chat_pdf = MagicMock()
        mock_chat_pdf.s3_service = mock_s3_service

        petition_bp = create_petition_blueprint(
            mock_chat_pdf, mock_email_service, mock_file_service
        )
        minimal_app.register_blueprint(petition_bp)

        # Add required config
        minimal_app.config["AWS_S3_PETITION_BUCKET_NAME"] = "test-petition-bucket"
        minimal_app.config["S3_BUCKET_NAME"] = "test-public-bucket"
        minimal_app.config["ELASTICSEARCH_HOST"] = "localhost"
        minimal_app.config["ELASTICSEARCH_PORT"] = 9200

        return minimal_app

    @pytest.fixture
    def petition_client(self, petition_app):
        return petition_app.test_client()

    @pytest.fixture
    def test_pdf(self):
        """Create a test PDF file for upload"""
        # Create a minimal valid PDF content
        pdf_content = b"%PDF-1.4\n%Test PDF content"
        return FileStorage(
            stream=BytesIO(pdf_content),
            filename="test_doc.pdf",
        )

    def test_public_doc_petition_no_file(
        self, petition_client, auth_headers, test_organization
    ):
        """Test upload without file"""
        response = petition_client.post(
            "/api/petition/public-doc-petition",
            data={
                "title": "Test Document",
                "organization_id": str(test_organization.id),
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert "No file provided" in response_data.get("message", "")

    def test_public_doc_petition_invalid_org(
        self, petition_client, auth_headers, test_pdf
    ):
        """Test upload with invalid organization"""
        response = petition_client.post(
            "/api/petition/public-doc-petition",
            data={
                "file": test_pdf,
                "title": "Test Document",
                "organization_id": str(
                    ObjectId()
                ),  # Random valid ObjectId that doesn't exist
            },
            headers=auth_headers,
        )

        print(f"Response data: {response.get_data(as_text=True)}")  # Debug print
        assert response.status_code == 400
        response_data = response.get_json()
        assert "Invalid organization ID" in response_data.get(
            "message", ""
        )  # Changed from ['error'] to .get('message', '')

    def test_public_doc_petition_duplicate_title(
        self,
        petition_client,
        auth_headers,
        test_pdf,
        test_file_metadata,
        test_organization,
    ):
        """Test upload with duplicate document title"""
        with petition_client.application.app_context():
            # Set up the test file metadata with the expected index
            test_file_metadata.index_names = ["FIX_DOC_PETITION_ROUTES_INDEX"]
            test_file_metadata.save()

            try:
                response = petition_client.post(
                    "/api/petition/public-doc-petition",
                    data={
                        "file": test_pdf,
                        "title": test_file_metadata.title,
                        "organization_id": str(test_organization.id),
                    },
                    headers=auth_headers,
                )

                print(f"Response data: {response.get_data(as_text=True)}")  # Debug
                assert response.status_code == 400
                response_data = response.get_json()
                assert "already exists" in response_data.get("message", "")

            finally:
                test_file_metadata.delete()

    def test_get_pending_documents_success(
        self, petition_client, auth_headers, test_user, test_organization
    ):
        """Test retrieving pending documents"""
        with petition_client.application.app_context():
            # Clean any existing pending documents first
            PendingDocument.objects.delete()

            # First ensure organization is saved and exists
            test_organization.save()

            # Create second organization directly
            second_org = Organization(
                name=f"Test Organization 2 {uuid.uuid4().hex[:8]}",
                slug_name="test-org-2",
                password=generate_password_hash("test_password"),
                index_name=f"test_index_{uuid.uuid4().hex[:8]}",
                email_suffix="test2.com",
            ).save()

            # Create documents after organizations are saved
            doc1 = PendingDocument(
                title="Test Doc 1",
                file_url="https://test.com/doc1.pdf",
                status="pending",
                from_user=test_user,
                target_organization=test_organization,
            ).save()

            doc2 = PendingDocument(
                title="Test Doc 2",
                file_url="https://test.com/doc2.pdf",
                status="pending",
                from_user=test_user,
                target_organization=second_org,
            ).save()

            try:
                response = petition_client.get(
                    "/api/petition/get_pending_documents", headers=auth_headers
                )

                print(f"Response data: {response.get_json()}")  # Debug

                assert response.status_code == 200
                response_data = response.get_json()

                # Verify we get both documents back
                assert len(response_data) == 2

                # Verify document fields
                org_names = {doc["organization_name"] for doc in response_data}
                assert test_organization.name in org_names
                assert second_org.name in org_names

            finally:
                # Clean up test data in correct order
                doc1.delete()
                doc2.delete()
                second_org.delete()

    def test_approve_document_success(
        self,
        petition_client,
        auth_headers,
        mock_file_service,
        mock_s3_service,
        test_user,
        test_organization,
    ):
        """Test successful document approval"""
        with petition_client.application.app_context(), patch(
            "tempfile.NamedTemporaryFile"
        ) as mock_temp:  # , patch("os.remove") as mock_remove
            # Create a real temporary file
            content = b"test pdf content"
            mock_file = BytesIO(content)
            mock_file.name = "/tmp/test.pdf"

            # Mock the file context manager
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_temp.return_value = mock_context

            # Mock S3 operations more completely
            mock_s3_service.s3_client.download_file.side_effect = (
                lambda bucket, key, filename: open(filename, "wb").write(content)
            )
            mock_s3_service.s3_client.upload_file.return_value = None
            mock_s3_service.s3_client.delete_object.return_value = None

            doc = PendingDocument(
                title="Test Doc",
                file_url="https://test.com/doc.pdf",
                status="pending",
                from_user=test_user,
                target_organization=test_organization,
            ).save()

            try:
                with open("/tmp/test.pdf", "wb") as f:  # Actually create the file
                    f.write(content)

                response = petition_client.post(
                    "/api/petition/approve_document",
                    json={
                        "document_id": str(doc.id),
                        "title": "Test Doc",
                        "index_name": "test_index",
                        "originating_user": str(test_user.id),
                    },
                    headers=auth_headers,
                )

                print(f"Response status: {response.status_code}")
                print(f"Response data: {response.get_data(as_text=True)}")
                print(f"Response headers: {response.headers}")
                print(f"Mock file service calls: {mock_file_service.mock_calls}")

                assert response.status_code == 200
                assert PendingDocument.objects(id=doc.id).first() is None
                mock_file_service.process_upload.assert_called_once()

            finally:
                # Clean up
                if os.path.exists("/tmp/test.pdf"):
                    os.remove("/tmp/test.pdf")
                if PendingDocument.objects(id=doc.id).first():
                    doc.delete()

    def test_approve_document_not_found(self, petition_client, auth_headers):
        """Test approval of non-existent document"""
        response = petition_client.post(
            "/api/petition/approve_document",
            json={
                "document_id": str(ObjectId()),
                "title": "Test Doc",
                "index_name": "test_index",
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        response_data = response.get_json()
        assert "Document not found" in response_data.get("message", "")

    def test_approve_document_missing_fields(
        self, petition_client, auth_headers, test_user, test_organization
    ):
        """Test approval with missing required fields"""
        doc = PendingDocument(
            title="Test Doc",
            file_url="https://test.com/doc.pdf",
            status="pending",
            from_user=test_user,
            target_organization=test_organization,
        ).save()

        response = petition_client.post(
            "/api/petition/approve_document",
            json={
                "document_id": str(doc.id)
                # Missing required fields
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        response_data = response.get_json()
        assert "Document ID and title are required" in response_data.get(
            "message", ""
        )  # Changed from 'error' to 'message'

        doc.delete()

    def test_reject_document_success(
        self,
        petition_client,
        auth_headers,
        mock_s3_service,
        test_user,
        test_organization,
    ):
        """Test successful document rejection"""
        doc = PendingDocument(
            title="Test Doc",
            file_url="https://test.com/doc.pdf",
            status="pending",
            from_user=test_user,
            target_organization=test_organization,
        ).save()

        response = petition_client.post(
            "/api/petition/reject_document",
            json={"document_id": str(doc.id)},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert PendingDocument.objects(id=doc.id).first() is None
        mock_s3_service.s3_client.delete_object.assert_called_once()

    def test_reject_document_not_found(self, petition_client, auth_headers):
        """Test rejection of non-existent document"""
        response = petition_client.post(
            "/api/petition/reject_document",
            json={"document_id": str(ObjectId())},
            headers=auth_headers,
        )

        assert response.status_code == 404
        response_data = response.get_json()
        assert "Document not found" in response_data.get("message", "")


# Add test to verify that endpoints can't be accessed as guests
