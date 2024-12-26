"""Factory for creating Flask app instances configured for integration testing."""

import pytest
import asyncio
from collections import defaultdict
from io import StringIO

from typing import Optional, Dict, Any, Tuple

from config.test import TestConfig
from tests.utils.provider_factory import TestProviderFactory
from factories.integration_app_factory import IntegrationAppFactory
from services.embedding_service import EmbeddingModel
from tests.integration.clients.base_client import BaseTestClient


class TestStats:
    """Enhanced test statistics collector with detailed metrics"""

    def __init__(self):
        self.test_times = {}
        self.api_calls = defaultdict(int)
        self.rate_limit_incidents = defaultdict(int)
        self.token_usage = defaultdict(lambda: {"input": 0, "output": 0, "total": 0})
        self.error_counts = defaultdict(lambda: defaultdict(int))
        self.slow_tests = []  # Tests taking longer than threshold
        self.test_status = defaultdict(lambda: {"status": "unknown", "error": None})

    def record_time(self, test_name: str, duration: float):
        """Record test execution time with slow test detection"""
        self.test_times[test_name] = duration
        if duration > 5.0:  # Threshold for slow tests
            self.slow_tests.append((test_name, duration))

    def record_api_call(self, test_name: str, provider: str = "unknown"):
        """Record API call with provider tracking"""
        self.api_calls[f"{test_name}:{provider}"] += 1

    def record_rate_limit(self, provider: str):
        """Track rate limit incidents by provider"""
        self.rate_limit_incidents[provider] += 1

    def record_token_usage(
        self, test_name: str, provider: str, input_tokens: int, output_tokens: int
    ):
        """Track token usage by test and provider"""
        key = f"{test_name}:{provider}"
        self.token_usage[key]["input"] += input_tokens
        self.token_usage[key]["output"] += output_tokens
        self.token_usage[key]["total"] += input_tokens + output_tokens

    def record_error(self, test_name: str, error_type: str):
        """Track errors by type and test"""
        self.error_counts[test_name][error_type] += 1

    def record_test_result(
        self, test_name: str, status: str, error: Optional[str] = None
    ):
        """Track test execution status and errors"""
        self.test_status[test_name] = {"status": status, "error": error}

    def generate_report(self) -> str:
        """Generate comprehensive test execution report"""
        output = StringIO()

        def write(text: str = ""):
            output.write(f"{text}\n")

        write("\n=== Detailed Test Statistics Report ===")

        # Test Execution Summary
        total_tests = len(self.test_times)
        passed_tests = sum(
            1 for status in self.test_status.values() if status["status"] == "passed"
        )
        failed_tests = sum(
            1 for status in self.test_status.values() if status["status"] == "failed"
        )

        write("\nTest Execution Summary:")
        write(f"Total Tests: {total_tests}")
        write(f"Passed: {passed_tests}")
        write(f"Failed: {failed_tests}")

        if self.slow_tests:
            write("\nSlow Tests (>5s):")
            for test, duration in sorted(
                self.slow_tests, key=lambda x: x[1], reverse=True
            ):
                write(f"  {test}: {duration:.2f}s")

        # API Usage
        if self.api_calls:
            write("\nAPI Usage by Provider:")
            provider_totals = defaultdict(int)
            for key, count in self.api_calls.items():
                test, provider = key.split(":")
                provider_totals[provider] += count
            for provider, total in sorted(
                provider_totals.items(), key=lambda x: x[1], reverse=True
            ):
                write(f"  {provider}: {total} calls")

        # Token Usage
        if self.token_usage:
            write("\nToken Usage by Provider:")
            for key, usage in sorted(
                self.token_usage.items(), key=lambda x: x[1]["total"], reverse=True
            ):
                test, provider = key.split(":")
                write(
                    f"  {provider} ({test}): {usage['total']} total tokens "
                    f"({usage['input']} input, {usage['output']} output)"
                )

        # Rate Limit Incidents
        if self.rate_limit_incidents:
            write("\nRate Limit Incidents:")
            for provider, count in sorted(
                self.rate_limit_incidents.items(), key=lambda x: x[1], reverse=True
            ):
                write(f"  {provider}: {count} incidents")

        # Error Distribution
        if any(self.error_counts.values()):
            write("\nError Distribution:")
            for test, errors in sorted(self.error_counts.items()):
                if errors:
                    write(f"\n{test}:")
                    for error_type, count in sorted(
                        errors.items(), key=lambda x: x[1], reverse=True
                    ):
                        write(f"    {error_type}: {count} occurrences")

        # Test Execution Times
        write("\nTest Execution Times:")
        for test, duration in sorted(
            self.test_times.items(), key=lambda x: x[1], reverse=True
        ):
            status = self.test_status[test]["status"]
            error = self.test_status[test]["error"]
            status_str = f" [{status}]" if status != "passed" else ""
            error_str = f" - {error}" if error else ""
            write(f"  {test}: {duration:.2f}s{status_str}{error_str}")

        return output.getvalue()


# Global test statistics instance
test_stats = TestStats()


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for each test function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def llm_service(request):
    """Provide LLM provider with proper isolation."""
    test_name = request.node.name
    provider_type = request.node.get_closest_marker("provider_type")
    provider_type = provider_type.args[0] if provider_type else "groq"
    return TestProviderFactory.create_llm_service(provider_type, test_name)


@pytest.fixture
def embedding_provider(request):
    """Provide embedding provider with proper isolation."""
    test_name = request.node.name
    provider_type = request.node.get_closest_marker("provider_type")
    provider_type = provider_type.args[0] if provider_type else "cohere"
    return TestProviderFactory.create_embedding_provider(provider_type, test_name)


@pytest.fixture
def embedding_model(request):
    """Provide embedding model with proper isolation."""
    test_name = request.node.name
    provider_type = request.node.get_closest_marker("provider_type")
    provider_type = provider_type.args[0] if provider_type else "cohere"
    return EmbeddingModel(
        TestProviderFactory.create_embedding_provider(provider_type, test_name)
    )


@pytest.fixture(autouse=True)
def setup_test_size(request):
    """Configure test size with validation."""
    marker = request.node.get_closest_marker("test_size")
    size = marker.args[0] if marker else "small"

    if size not in ["small", "medium", "large"]:
        pytest.fail(f"Invalid test size: {size}. Must be small, medium, or large")

    test_config = TestConfig()
    test_config.TEST_SIZE = size

    # Set the test config in the factory
    TestProviderFactory.set_test_config(test_config)

    yield

    # Reset to small for safety
    test_config.TEST_SIZE = "small"
    TestProviderFactory.set_test_config(test_config)


@pytest.fixture
def integration_client(request):
    """Create an integration test client with proper configuration."""


@pytest.fixture
def test_app(request):
    """Create Flask app for testing with proper configuration."""
    # Get test size and required blueprints from markers
    size_marker = request.node.get_closest_marker("test_size")
    size = size_marker.args[0] if size_marker else "small"

    blueprint_marker = request.node.get_closest_marker("blueprints")
    blueprints = blueprint_marker.args[0] if blueprint_marker else "all"

    # Create app with appropriate configuration
    app = IntegrationAppFactory.create_app(
        test_name=request.node.name,
        blueprints=blueprints,
        enable_rate_limits=size != "small",  # Enable rate limits for medium/large tests
    )
    return app


@pytest.fixture
def base_test_client(test_app) -> BaseTestClient:
    """Provide configured base test client."""
    return BaseTestClient(test_app)


@pytest.fixture
def test_client(base_test_client):
    """
    Provide raw Flask test client.
    Deprecated: Prefer using base_test_client for better utilities and auth handling.
    """
    return base_test_client.test_client


@pytest.fixture
def registered_user(
    base_test_client: BaseTestClient,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Create a test user and return (user_data, auth_headers).

    Usage:
        # Function-based tests
        def test_something(registered_user):
            user_data, headers = registered_user
            # Use headers for auth

        # Class-based tests
        class TestSomething:
            @pytest.fixture(autouse=True)
            def setup(self, registered_user):
                self.user_data, self.headers = registered_user
    """
    return base_test_client.register_test_user()


@pytest.fixture
def auth_headers(registered_user) -> Dict[str, str]:
    """
    Provide auth headers for backward compatibility.
    Deprecated: Prefer using registered_user fixture directly.
    """
    _, headers = registered_user
    return headers


def pytest_configure(config):
    """Register custom markers and set asyncio mode."""
    config.addinivalue_line(
        "markers",
        "test_size(size): mark test with specific size requirement (small, medium, large)",
    )
    config.addinivalue_line(
        "markers",
        "blueprints(list): specify which blueprints to load for the test",
    )
    config.addinivalue_line(
        "markers",
        "provider_type(type): specify which provider type to use for the test",
    )

    # Set asyncio mode to auto
    config.option.asyncio_mode = "auto"


def pytest_runtest_setup(item):
    """Skip external service tests unless explicitly enabled."""
    marker = item.get_closest_marker("test_size")
    size = marker.args[0] if marker else "small"

    test_config = TestConfig()
    test_config.TEST_SIZE = size

    if "external_service" in item.keywords and not test_config.is_using_real_apis():
        pytest.skip("External service tests are disabled")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print test statistics at the end of the test session."""
    report = test_stats.generate_report()
    terminalreporter.write_line(report)
