from typing import List
import pytest
from flask import Flask
from flask_mail import Mail
from unittest.mock import MagicMock
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config.test import TestConfig
from services.email_service import EmailService
from services.embedding_service import EmbeddingModel
from services.organization_service import OrganizationService
from services.user_service import UserService
from services.auth_service import AuthService
from .database import connect_test_db, clean_db_collections, get_test_db_name


def create_minimal_app(blueprints: List[str] = None) -> Flask:
    """
    Create a minimal Flask app with only specified blueprints.
    This is a helper function for the minimal_app fixture.
    """
    app = Flask(__name__)
    app.config.from_object(TestConfig)

    # Use unique database name for parallel testing
    db_name = get_test_db_name()
    app.config["MONGODB_DB"] = db_name
    app.config["MONGODB_HOST"] = f"mongodb://mongo:27019/{db_name}"

    # Initialize minimal required services
    mail = Mail(app)
    email_service = EmailService(mail)

    # Mock embedding model for tests
    mock_embedding_model = MagicMock(spec=EmbeddingModel)
    mock_embedding_model.embed.return_value = [0] * app.config["DEFAULT_EMBEDDING_DIMS"]

    # Initialize services with mocked dependencies
    mock_index_service = MagicMock()
    organization_service = OrganizationService(index_service=mock_index_service)
    user_service = UserService(index_service=mock_index_service)

    blueprints = blueprints or []

    # Register requested blueprints
    if "auth" in blueprints:
        from blueprints.auth_routes import create_auth_blueprint

        auth_service = AuthService(
            email_service, app.config["SECRET_KEY"], user_service
        )
        app.register_blueprint(
            create_auth_blueprint(
                auth_service, email_service, organization_service, user_service
            )
        )

    if "user" in blueprints:
        from blueprints.user_routes import create_user_blueprint

        limiter = Limiter(get_remote_address, app=app, enabled=False)

        app.register_blueprint(
            create_user_blueprint(limiter, user_service, organization_service)
        )

    if "organization" in blueprints:
        from blueprints.organization_routes import create_organization_blueprint

        app.register_blueprint(
            create_organization_blueprint(email_service, organization_service)
        )

    return app


@pytest.fixture
def minimal_app(request):
    """
    Create a minimal Flask app for testing with only specified blueprints.
    Usage:
        @pytest.mark.blueprints(['auth'])  # Only include auth blueprint
        def test_something(minimal_app):
            ...
    """
    marker = request.node.get_closest_marker("blueprints")
    blueprints = marker.args[0] if marker else []

    app = create_minimal_app(blueprints)

    # Initialize test database after app creation
    connect_test_db(app)

    yield app

    # Clean up collections after each test
    clean_db_collections()


@pytest.fixture
def minimal_client(minimal_app):
    """Test client using minimal app"""
    return minimal_app.test_client()


@pytest.fixture
def mock_limiter():
    """Create a mock rate limiter for testing."""

    class MockDecorator:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __call__(self, f):
            def decorated(*args, **kwargs):
                return f(*args, **kwargs)

            return decorated

    class MockLimiter:
        def limit(self, *args, **kwargs):
            return MockDecorator(*args, **kwargs)

        def exempt(self):
            return MockDecorator()

        def reset(self):
            pass

    return MockLimiter()


def pytest_runtest_setup(item):
    """Setup for individual tests"""
    # Skip external service tests unless explicitly enabled
    if "external_service" in item.keywords and not TestConfig.ENABLE_EXTERNAL_SERVICES:
        pytest.skip("External service tests are disabled")
