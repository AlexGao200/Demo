import pytest
from datetime import datetime, timezone, timedelta
from models.user import User
from models.organization import Organization
from models.user_organization import UserOrganization
from models.pending import PendingRequest
from auth.utils import generate_token
from werkzeug.security import generate_password_hash
import uuid


@pytest.mark.blueprints(["organization", "auth"])  # Added auth since it's likely needed
class TestOrganizationRoutes:
    @pytest.fixture
    def org_admin_user(test_user, test_organization):
        """Create a user with admin privileges for organization testing"""
        UserOrganization(
            user=test_user, organization=test_organization, role="admin"
        ).save()
        return test_user

    @pytest.fixture
    def org_client(self, minimal_app):
        """Use the minimal_app directly since blueprint is registered via marker"""
        return minimal_app.test_client()

    def test_create_organization_success(
        self, org_client, auth_headers, test_user, mock_index_service
    ):
        """Test successful organization creation"""
        # Setup debug tracing
        org_name = f"Test Organization {uuid.uuid4().hex[:8]}"
        print(f"\nStarting test with org_name: {org_name}")
        print(f"Mock index service: {mock_index_service}")

        try:
            response = org_client.post(
                "/api/organization/create_organization",
                json={
                    "name": org_name,
                    "organization_password": "Test12345",
                    "email_suffix": "@test.com",  # Remove @ prefix
                },
                headers=auth_headers,
            )

            print(f"\nResponse status: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)}")

            assert response.status_code == 201
            data = response.get_json()
            assert "organization_id" in data

            # Debug the created organization
            org = Organization.objects(name=org_name).first()
            print("\nCreated organization:")
            print(f"ID: {org.id}")
            print(f"Name: {org.name}")
            print(f"Index name: {org.index_name}")

            assert org is not None
            assert org.email_suffix == "@test.com"

            # Verify index service calls
            print("\nVerifying mock calls:")
            for call in mock_index_service.create_organization_index.mock_calls:
                print(f"Call: {call}")

        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print(f"Type: {type(e)}")
            raise

    def test_get_organization_members(
        self, org_client, auth_headers, test_user, test_organization
    ):
        """Test retrieving organization members"""
        response = org_client.get(
            f"/api/organization/{test_organization.id}/members", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "members" in data
        members = data["members"]
        assert len(members) > 0

        # Verify test user is in members list
        member = next((m for m in members if m["id"] == str(test_user.id)), None)
        assert member is not None
        assert member["role"] == "admin"

    def test_add_admin_success(
        self, org_client, auth_headers, test_organization, test_user_data
    ):
        """Test adding a new admin to organization"""
        # Create a new user to add as admin
        from models.user import User

        new_user = User(
            email="newadmin@test.com",
            username="newadmin",
            password=generate_password_hash("test123"),
            first_name="New",
            last_name="Admin",
        ).save()

        try:
            response = org_client.post(
                "/api/organization/add_admin",
                json={
                    "organization_id": str(test_organization.id),
                    "password": "test_password",  # From conftest
                    "email": "newadmin@test.com",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify user was added as admin
            user_org = UserOrganization.objects(
                user=new_user.id, organization=test_organization.id
            ).first()
            assert user_org is not None
            assert user_org.role == "admin"

        finally:
            new_user.delete()

    def test_submit_join_request(
        self, org_client, auth_headers, test_organization, test_user
    ):
        """Test submitting a join request"""
        response = org_client.post(
            "/api/organization/join-request",
            json={
                "organization_id": str(test_organization.id),
                "message": "Please let me join",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

        # Verify request was created with required fields
        request = PendingRequest.objects(
            user=test_user, organization=test_organization
        ).first()

        assert request is not None
        assert request.first_name == test_user.first_name  # Verify first_name is set
        assert request.last_name == test_user.last_name  # Verify last_name is set
        assert request.request_message == "Please let me join"

    def test_approve_join_request(
        self, org_client, auth_headers, test_organization, test_user, minimal_app
    ):
        """Test approving a join request"""
        request = None
        user_org = None

        try:
            # First remove any existing organization memberships
            UserOrganization.objects(
                user=test_user, organization=test_organization
            ).delete()

            # Create a pending request with all required fields
            request = PendingRequest(
                user=test_user,
                first_name=test_user.first_name,
                last_name=test_user.last_name,
                organization=test_organization,
                request_message="Test request",
                status="pending",
            ).save()

            # Create admin user to approve the request
            admin_user = User(
                email="admin@test.com",
                username="admin_user",
                password="test123",
                first_name="Admin",
                last_name="User",
                is_verified=True,
                personal_index_name="test_admin_index",  # Add this
                is_superadmin=False,  # Add this
                subscription_status="active",  # Add this
            ).save()

            # Make the new user an admin
            admin_org = UserOrganization(
                user=admin_user,
                organization=test_organization,
                role="admin",
                index_name=test_organization.index_name,
            ).save()

            # Create auth headers for admin user with all required fields
            admin_user_data = {
                "id": str(admin_user.id),
                "username": admin_user.username,
                "email": admin_user.email,
                "first_name": admin_user.first_name,
                "last_name": admin_user.last_name,
                "personal_index_name": admin_user.personal_index_name,
                "is_superadmin": admin_user.is_superadmin,
                "subscription_status": "active",
                "cycle_token_limit": 1000,
                "last_login": datetime.now(timezone.utc),
                "organization_indices": [
                    test_organization.index_name
                ],  # Add organization indices
            }

            admin_token = generate_token(
                user_data=admin_user_data,
                secret_key=minimal_app.config["SECRET_KEY"],
                expires_in=timedelta(days=1),
            )

            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            }

            # Now try to approve the request as admin
            response = org_client.post(
                "/api/organization/approve-request",
                json={
                    "request_id": str(request.id),
                    "approve": True,
                    "organization_id": str(test_organization.id),
                    "membershipType": "paid",
                },
                headers=admin_headers,
            )

            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)}")

            assert response.status_code == 200

            # Verify test_user was added as member
            user_org = UserOrganization.objects(
                user=test_user.id, organization=test_organization.id
            ).first()
            assert user_org is not None
            assert user_org.is_paid is True
            assert user_org.role == "member"  # Should be member, not admin

            # Verify request was deleted
            assert PendingRequest.objects(id=request.id).first() is None

        finally:
            # Clean up
            if request and PendingRequest.objects(id=request.id).first():
                request.delete()
            if user_org and UserOrganization.objects(id=user_org.id).first():
                user_org.delete()
            UserOrganization.objects(
                user=test_user.id, organization=test_organization.id
            ).delete()
            if "admin_user" in locals():
                admin_org.delete()
                admin_user.delete()

    def test_update_member_role(
        self, org_client, auth_headers, test_organization, test_user
    ):
        """Test updating a member's role"""
        response = org_client.post(
            "/api/organization/update_member_role",
            json={
                "username": test_user.username,
                "new_role": "member",
                "organization_id": str(test_organization.id),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify role was updated
        user_org = UserOrganization.objects(
            user=test_user.id, organization=test_organization.id
        ).first()
        assert user_org.role == "member"

    def test_authentication(self, org_client, test_organization):
        """Test organization authentication"""
        response = org_client.post(
            "/api/organization/authenticate",
            json={
                "org_id": str(test_organization.id),
                "password": "test_password",  # From conftest
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "org_token" in response.headers.get("Set-Cookie", "")

    def test_get_organization_details(
        self, org_client, auth_headers, test_organization
    ):
        """Test retrieving organization details"""
        response = org_client.get(
            f"/api/organization/{test_organization.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == test_organization.name
        assert "members" in data
        assert "index_name" in data
