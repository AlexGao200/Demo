"""Organization test client for integration tests."""

from .base_client import BaseTestClient


class OrganizationTestClient(BaseTestClient):
    """Test client for organization-related operations"""

    def create_organization(self, auth_headers, org_name, password, email_suffix):
        """Create an organization"""
        response = self.app.test_client().post(
            "/api/organization/create_organization",
            json={
                "name": org_name,
                "organization_password": password,
                "email_suffix": email_suffix,
            },
            headers=auth_headers,
        )
        self._log_response(response, "Create Organization")
        return response

    def change_user_role(self, auth_headers, username, new_role, organization_id):
        """Change a user's role in an organization"""
        response = self.app.test_client().post(
            "/api/organization/update_member_role",
            json={
                "username": username,
                "new_role": new_role,
                "organization_id": organization_id,
            },
            headers=auth_headers,
        )
        self._log_response(response, "Change User Role")
        return response

    def check_admin_access(self, auth_headers, organization_id):
        """Check admin access for an organization"""
        response = self.app.test_client().post(
            "/api/organization/check_admin_access",
            json={"organization_id": organization_id},
            headers=auth_headers,
        )
        self._log_response(response, "Check Admin Access")
        return response

    def authenticate_admin(self, org_id, password):
        """Authenticate as an organization admin"""
        response = self.app.test_client().post(
            "/api/organization/authenticate",
            json={"org_id": org_id, "password": password},
        )
        self._log_response(response, "Authenticate Admin")
        return response

    def get_organization_details(self, auth_headers, organization_id):
        """Get organization details"""
        response = self.app.test_client().get(
            f"/api/organization/{organization_id}",
            headers=auth_headers,
        )
        self._log_response(response, "Get Organization Details")
        return response

    def send_invitation(self, auth_headers, email, organization_id):
        """Send an invitation to join the organization"""
        response = self.app.test_client().post(
            "/api/organization/invite",
            json={"email": email, "organization_id": organization_id},
            headers=auth_headers,
        )
        self._log_response(response, "Send Invitation")
        return response

    def submit_join_request(self, auth_headers, organization_id, message=""):
        """Submit a request to join an organization"""
        response = self.app.test_client().post(
            "/api/organization/join-request",
            json={
                "organization_id": organization_id,
                "message": message or "I would like to join this organization",
            },
            headers=auth_headers,
        )
        self._log_response(response, "Submit Join Request")
        return response

    def get_pending_requests(self, auth_headers, organization_id):
        """Get pending join requests for an organization"""
        response = self.app.test_client().get(
            f"/api/organization/pending-requests/{organization_id}",
            headers=auth_headers,
        )
        self._log_response(response, "Get Pending Requests")
        return response

    def approve_join_request(
        self,
        auth_headers,
        request_id,
        organization_id,
        approve=True,
        membership_type="free",
    ):
        """Approve or reject a join request"""
        response = self.app.test_client().post(
            "/api/organization/approve-request",
            json={
                "request_id": request_id,
                "approve": approve,
                "membershipType": membership_type,
                "organization_id": organization_id,
            },
            headers=auth_headers,
        )
        self._log_response(response, "Approve Join Request")
        return response

    def delete_organization(self, auth_headers, organization_id):
        """Delete an organization"""
        response = self.app.test_client().delete(
            f"/api/organization/{organization_id}",
            headers=auth_headers,
            json={"organization_id": organization_id},
        )
        self._log_response(response, "Delete Organization")
        return response
