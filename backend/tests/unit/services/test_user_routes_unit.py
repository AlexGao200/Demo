import pytest
from bson import ObjectId
from models.user import User
from models.organization import Organization
from models.user_organization import UserOrganization
from werkzeug.security import generate_password_hash


@pytest.mark.blueprints(["user", "auth"])
class TestUserRoutes:
    @pytest.fixture
    def second_user(self, valid_user_data):
        """Create a second test user for organization tests"""
        user_data = valid_user_data.copy()
        user_data["email"] = f"second_{user_data['email']}"
        user_data["username"] = f"second_{user_data['username']}"
        user = User(**user_data).save()
        yield user
        user.delete()

    def test_delete_user_success(self, minimal_client, test_user, auth_headers):
        """Test successful user deletion"""
        with minimal_client.application.app_context():
            response = minimal_client.delete(
                f"/api/user/{str(test_user.id)}",
                headers=auth_headers,
                json={"reason": "leaving platform"},
            )

            assert response.status_code == 200

            # Verify user is soft deleted but still exists
            updated_user = User.objects.get(id=test_user.id)
            assert updated_user.is_deleted
            # Check that email is changed to deleted placeholder
            assert updated_user.email.startswith("deleted_user_")
            assert updated_user.email.endswith("@deleted.user")
            # Verify username is also anonymized
            assert updated_user.username.startswith("deleted_user_")

    def test_join_organization(self, minimal_client, test_user, auth_headers):
        """Test user joining an organization"""
        with minimal_client.application.app_context():
            # Create a new organization for the test
            org = Organization(
                name=f"Test Org {ObjectId()}",
                slug_name="test-org",
                password=generate_password_hash("test123"),
                index_name=f"test_index_{ObjectId()}",
                email_suffix="test.com",
            ).save()

            try:
                response = minimal_client.post(
                    "/api/join-organization",
                    json={
                        "org_id": str(org.id),
                        "user_id": str(test_user.id),
                        "role": "member",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 200

                # Verify membership
                user_org = UserOrganization.objects(
                    user=test_user, organization=org
                ).first()
                assert user_org is not None
                assert user_org.role == "member"

            finally:
                org.delete()

    def test_set_initial_organization(
        self, minimal_client, test_user, test_organization, auth_headers
    ):
        """Test setting user's initial organization"""
        with minimal_client.application.app_context():
            response = minimal_client.post(
                f"/api/user/{str(test_user.id)}/set_initial_organization",
                json={"organization_id": str(test_organization.id)},
                headers=auth_headers,
            )

            assert response.status_code == 200

            updated_user = User.objects.get(id=test_user.id)
            assert updated_user.initial_organization == test_organization

    def test_get_user_organizations(
        self, minimal_client, test_user, test_organization, auth_headers
    ):
        """Test retrieving user's organizations"""
        with minimal_client.application.app_context():
            response = minimal_client.get(
                f"/api/user/{str(test_user.id)}/organizations", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            orgs = data["organizations"]
            assert len(orgs) >= 1  # Should have at least test_organization

            test_org = next(
                org for org in orgs if str(org["id"]) == str(test_organization.id)
            )
            assert test_org["name"] == test_organization.name
            assert test_org["index_name"] == test_organization.index_name
            assert "role" in test_org

    def test_leave_organization(
        self, minimal_client, test_user, test_organization, auth_headers
    ):
        """Test user leaving an organization"""
        with minimal_client.application.app_context():
            response = minimal_client.post(
                f"/api/user/{str(test_user.id)}/leave-organization",
                json={"org_id": str(test_organization.id)},
                headers=auth_headers,
            )

            assert response.status_code == 200

            user_org = UserOrganization.objects(
                user=test_user, organization=test_organization
            ).first()
            assert user_org is None

    def test_get_user_roles(
        self, minimal_client, test_user, test_organization, auth_headers
    ):
        """Test retrieving user's roles across organizations"""
        with minimal_client.application.app_context():
            response = minimal_client.get(
                f"/api/user/{str(test_user.id)}/roles", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()

            # Should have role for test_organization
            assert str(test_organization.id) in data["roles"]
            assert data["roles"][str(test_organization.id)] in [
                "admin",
                "member",
                "editor",
            ]

    def test_set_user_token_limit(self, minimal_client, test_user, auth_headers):
        """Test updating user's token limit"""
        with minimal_client.application.app_context():
            new_limit = 2000
            response = minimal_client.post(
                f"/api/user/{str(test_user.id)}/token_limit",
                json={"token_limit": new_limit},
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify token limit is updated
            updated_user = User.objects.get(id=test_user.id)
            assert updated_user.cycle_token_limit == new_limit
