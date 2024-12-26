import pytest
import requests
import os


@pytest.mark.e2e
class TestUserJourney:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and configuration"""
        self.base_url = os.getenv("BACKEND_URL", "http://localhost:5000")
        self.test_user = {
            "username": f"test_user_{os.urandom(8).hex()}",
            "email": f"test_{os.urandom(8).hex()}@example.com",
            "password": "test_password",
        }
        self.session = requests.Session()

        yield

        # Cleanup: Delete test user
        if hasattr(self, "auth_token"):
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            self.session.delete(
                f"{self.base_url}/api/users/{self.test_user['username']}"
            )

    def test_full_user_journey(self):
        """Test complete user journey from registration to data access"""
        # 1. Register
        register_response = self.session.post(
            f"{self.base_url}/auth/register", json=self.test_user
        )
        assert register_response.status_code == 201

        # 2. Login
        login_response = self.session.post(
            f"{self.base_url}/auth/login",
            json={
                "username": self.test_user["username"],
                "password": self.test_user["password"],
            },
        )
        assert login_response.status_code == 200
        self.auth_token = login_response.json()["token"]

        # 3. Access protected resource
        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        profile_response = self.session.get(f"{self.base_url}/api/users/me")
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == self.test_user["username"]
