"""
Main conftest.py that imports and exposes all fixtures.
Fixtures are organized by module but available globally.
"""

# Import all fixtures from their respective modules
pytest_plugins = [
    # App and core setup
    "tests.unit.fixtures.app",
    "tests.unit.fixtures.auth",
    "tests.unit.fixtures.database",
    # Services
    "tests.unit.fixtures.services.elasticsearch",
    "tests.unit.fixtures.services.email",
    "tests.unit.fixtures.services.s3",
    "tests.unit.fixtures.services.organization",
    "tests.unit.fixtures.services.guest",
    "tests.unit.fixtures.services.chat",
    # Models
    "tests.unit.fixtures.models.user",
    "tests.unit.fixtures.models.organization",
    "tests.unit.fixtures.models.file",
]


def pytest_configure(config):
    """Configure pytest for the test suite"""
    config.addinivalue_line(
        "markers", "external_service: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "blueprints: mark test as requiring specific blueprints"
    )
