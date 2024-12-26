import pytest
from flask_mail import Message
from services.email_service import EmailService
from services.llm_service import LLM
import anthropic
import requests
import os


def requires_external_services(func):
    """Decorator to mark tests that require external services"""
    return pytest.mark.skipif(
        not os.getenv("RUN_EXTERNAL_TESTS"),
        reason="Test requires external services. Set RUN_EXTERNAL_TESTS=1 to run",
    )(func)


@requires_external_services
class TestExternalConnections:
    """
    Smoke tests for external service connections.
    Run with: RUN_EXTERNAL_TESTS=1 pytest tests/e2e/smoke/test_external_connections.py -v
    """

    def test_email_connection(self, app):
        """Verify email server connection and sending capability"""
        with app.app_context():
            try:
                msg = Message(
                    "Test Connection",
                    sender=app.config["MAIL_DEFAULT_SENDER"],
                    recipients=[app.config["MAIL_DEFAULT_SENDER"]],  # Send to self
                )
                msg.body = "This is a test email to verify SMTP connection"

                mail = EmailService()
                mail.send(msg)
                assert True, "Email sent successfully"
            except Exception as e:
                pytest.fail(f"Failed to send email: {str(e)}")

    def test_llm_connection(self):
        """Verify LLM API connection with structured system messages"""
        try:
            client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))
            system_prompts = [
                {
                    "type": "text",
                    "text": "You are a helpful assistant for testing connections.",
                }
            ]
            llm = LLM(client, system_prompts=system_prompts)

            response = llm.invoke(
                "Echo back: TEST_CONNECTION_OK", model_id="claude-3-opus-20240229"
            )
            assert "TEST_CONNECTION_OK" in response.content
        except Exception as e:
            pytest.fail(f"Failed to connect to LLM API: {str(e)}")

    def test_elasticsearch_connection(self, app):
        """Verify Elasticsearch connection"""
        with app.app_context():
            try:
                es_host = app.config["ELASTICSEARCH_HOST"]
                es_port = app.config["ELASTICSEARCH_PORT"]
                es_user = app.config["ELASTICSEARCH_USER"]
                es_pass = app.config["ELASTICSEARCH_PASSWORD"]

                url = f"http://{es_host}:{es_port}"
                response = requests.get(
                    url, auth=(es_user, es_pass) if es_user and es_pass else None
                )
                assert response.status_code == 200
            except Exception as e:
                pytest.fail(f"Failed to connect to Elasticsearch: {str(e)}")

    def test_stripe_connection(self, app):
        """Verify Stripe API connection"""
        with app.app_context():
            import stripe

            try:
                stripe.api_key = app.config["STRIPE_SECRET_KEY"]
                # Just list a single customer to verify connection
                stripe.Customer.list(limit=1)
                assert True, "Successfully connected to Stripe API"
            except Exception as e:
                pytest.fail(f"Failed to connect to Stripe API: {str(e)}")
