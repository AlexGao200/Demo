import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import json
import os
import uuid
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash
from io import BytesIO
from models.organization import Organization
from models.user_organization import UserOrganization
from models.action_log import ActionLog
from models.index_registry import IndexRegistry


@pytest.mark.blueprints(["file"])
class TestFileRoutes:
    @pytest.fixture
    def mock_file_service(self):
        mock = MagicMock()

        async def mock_process_upload(
            file,
            title,
            index_name,
            file_visibility="private",
            user_id=None,
            nominal_creator_name=None,
            filter_dimensions=None,
        ):
            return {
                "file_metadata": {
                    "id": "123",
                    "title": title,
                    "index_names": [index_name],
                    "s3_url": "https://test-bucket.s3.amazonaws.com/test.pdf",
                }
            }

        mock.process_upload = AsyncMock(side_effect=mock_process_upload)
        mock.delete_document = AsyncMock(
            return_value=({"message": "Document deleted"}, 200)
        )
        return mock

    @pytest.mark.blueprints(["file"])
    class TestFileRoutes:
        @pytest.fixture
        def test_index(self, test_organization):
            """Create test index registry entry"""
            index = IndexRegistry(
                index_name=test_organization.index_name,
                display_name="Test Index",
                filter_dimensions={},
                created_at=datetime.now(timezone.utc),
            ).save()
            yield index
            index.delete()

    @pytest.fixture
    def file_app(self, minimal_app, mock_file_service, mock_s3_service):
        """Configure minimal app with file blueprint"""
        from blueprints.file_routes import create_file_blueprint
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        limiter = Limiter(
            app=minimal_app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
        )

        mock_chat_pdf = MagicMock()
        mock_chat_pdf.s3_service = mock_s3_service

        file_bp = create_file_blueprint(mock_chat_pdf, mock_file_service, limiter)
        minimal_app.register_blueprint(file_bp)
        tmp_dir = "/tmp"
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, mode=0o777)

        minimal_app.config["TMP_DIR"] = tmp_dir

        return minimal_app

    @pytest.fixture
    def file_client(self, file_app):
        return file_app.test_client()

    @pytest.fixture
    def test_pdf(self):
        """Create a test PDF file"""
        pdf_content = b"%PDF-1.4\n%Test PDF content"
        return FileStorage(
            stream=BytesIO(pdf_content),
            filename="test.pdf",
        )

    def test_unified_upload_invalid_permissions(
        self, file_client, auth_headers, test_pdf
    ):
        """Test upload with invalid organization permissions"""
        # Create organization without user permissions
        org = Organization(
            name=f"No Access Org {uuid.uuid4().hex[:8]}",  # Unique name
            slug_name="no-access",
            index_name=f"no_access_index_{uuid.uuid4().hex[:8]}",  # Unique index
            email_suffix="test.com",
            password=generate_password_hash("test_password"),  # Added required password
        ).save()

        data = {
            "files": [(test_pdf, "test.pdf")],
            "titles": ["Test Document"],
            "file_visibilities": json.dumps(["private"]),
            "index_names": org.index_name,
            "filter_dimensions": json.dumps({}),
        }

        response = file_client.post(
            "/api/upload",
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 403
        org.delete()

    def test_unified_upload_success(
        self,
        file_client,
        auth_headers,
        test_pdf,
        test_organization,
        test_index_registry,
        file_app,
    ):
        """Test successful file upload"""
        with file_app.app_context():
            data = {
                "files": [(test_pdf, "test.pdf")],
                "titles": ["Test Document"],
                "file_visibilities": json.dumps(["private"]),
                "index_names": test_organization.index_name,
                "filter_dimensions": json.dumps({}),
            }

            response = file_client.post(
                "/api/upload",
                data=data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            response_data = response.get_json()
            assert "results" in response_data
            assert len(response_data["results"]) == 1

    @pytest.mark.parametrize(
        "role", ["member", "none"]
    )  # Changed from "viewer" to "member"
    def test_delete_document_insufficient_permissions(
        self,
        file_client,
        auth_headers,
        test_file_metadata,
        role,
        test_user,
        test_organization,
    ):
        """Test deletion with insufficient permissions"""
        if role != "none":
            # Update existing UserOrganization
            user_org = UserOrganization.objects.get(
                user=test_user, organization=test_organization
            )
            user_org.role = role  # Now using 'member' which is a valid role
            user_org.save()
        else:
            # Remove user's organization access completely
            UserOrganization.objects(
                user=test_user, organization=test_organization
            ).delete()

        response = file_client.delete(
            f"/api/file/{str(test_file_metadata.id)}", headers=auth_headers
        )

        assert response.status_code == 403

    def test_get_file_info_success(self, file_client, auth_headers, test_file_metadata):
        """Test successful file info retrieval"""
        response = file_client.get(
            f"/api/file/{str(test_file_metadata.id)}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == test_file_metadata.title
        assert data["s3_url"] == test_file_metadata.s3_url
        assert data["index_names"] == test_file_metadata.index_names
        assert data["index_display_name"] == test_file_metadata.index_display_name

    def test_get_file_info_not_found(self, file_client, auth_headers):
        """Test retrieval of non-existent file"""
        response = file_client.get(
            "/api/file/000000000000000000000000", headers=auth_headers
        )

        assert response.status_code == 404

    def test_serve_tmp_file_success(
        self, file_client, auth_headers, test_pdf, test_chat, file_app
    ):
        """Test successful temporary file serving"""
        filename = "test.pdf"

        with file_app.app_context():
            filepath = os.path.join(file_app.config["TMP_DIR"], filename)
            print(f"Writing file to: {filepath}")  # Debug print

            try:
                # Write test file
                with open(filepath, "wb") as f:
                    test_pdf.seek(0)
                    f.write(test_pdf.read())

                print(f"File exists: {os.path.exists(filepath)}")  # Debug print
                print(
                    f"File permissions: {oct(os.stat(filepath).st_mode)[-3:]}"
                )  # Debug print

                response = file_client.get(
                    f"/api/tmp/{filename}?chat_id={str(test_chat.id)}",
                    headers=auth_headers,
                )

                if response.status_code != 200:
                    print(f"Response status: {response.status_code}")  # Debug print
                    print(
                        f"Response data: {response.get_data(as_text=True)}"
                    )  # Debug print

                assert response.status_code == 200

            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

    def test_get_file_info_no_permission(
        self, file_client, auth_headers, test_file_metadata, test_user
    ):
        """Test retrieval when user loses access to organization"""
        # Remove user's organization access
        UserOrganization.objects(user=test_user).delete()

        response = file_client.get(
            f"/api/file/{str(test_file_metadata.id)}", headers=auth_headers
        )

        assert response.status_code == 403

    def test_delete_document_success(
        self, file_client, auth_headers, test_file_metadata, mock_file_service
    ):
        """Test successful document deletion"""
        response = file_client.delete(
            f"/api/file/{str(test_file_metadata.id)}", headers=auth_headers
        )

        assert response.status_code == 200
        assert ActionLog.objects(action_type="delete_doc").count() == 1
        mock_file_service.delete_document.assert_called_once()
