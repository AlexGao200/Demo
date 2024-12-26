import pytest
import requests
import os


@pytest.mark.smoke
def test_api_health():
    """Smoke test for API health check"""
    # Get base URL from environment
    base_url = os.getenv("BACKEND_URL", "http://localhost:5000")

    # Test health endpoint
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200

    # Verify essential services
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["elasticsearch"] == "connected"
    assert health_data["mongodb"] == "connected"


@pytest.mark.smoke
def test_critical_auth_flow():
    """Smoke test for critical auth flow"""
    base_url = os.getenv("BACKEND_URL", "http://localhost:5000")

    # Test login endpoint availability
    response = requests.post(
        f"{base_url}/auth/login",
        json={"username": "smoke_test", "password": "test_pass"},
    )
    # We expect 401 for invalid creds, 500 would be concerning
    assert response.status_code in [200, 401]
