import pytest
from unittest.mock import MagicMock

from config.test import TestConfig

test_config = TestConfig()


@pytest.fixture
def mock_stripe():
    """
    Simplified Stripe mock that only implements what tests actually use.
    Add more mock implementations as needed by tests.
    """
    if test_config.ENABLE_EXTERNAL_SERVICES:
        pytest.skip("Using real Stripe service")

    mock = MagicMock()

    # Basic customer operations
    mock.Customer.create.return_value = {"id": "cus_test", "email": "test@example.com"}
    mock.Customer.retrieve.return_value = {
        "id": "cus_test",
        "email": "test@example.com",
    }

    # Basic subscription operations
    mock.Subscription.create.return_value = {
        "id": "sub_test",
        "status": "active",
        "current_period_start": 1729145600,
        "current_period_end": 1729232000,
    }
    mock.Subscription.modify.return_value = {
        "id": "sub_test123",
        "status": "active",
        "current_period_end": 1729232000,
        "cancel_at_period_end": True,
    }
    mock.Subscription.retrieve.return_value = {
        "id": "sub_test123",
        "items": {"data": [{"id": "item_test123", "price": {"id": "price_test123"}}]},
    }

    # Mock Price methods
    mock.Price.retrieve.return_value = {
        "id": "price_test123",
        "product": "prod_test123",
        "unit_amount": 10000,
        "currency": "usd",
    }

    # Mock Product methods
    mock.Product.retrieve.return_value = {"id": "prod_test123", "name": "Pro Plan"}

    # Mock Invoice methods
    mock.Invoice.list.return_value = {
        "data": [
            {
                "id": "inv_test123",
                "amount_due": 5000,
                "currency": "usd",
                "status": "paid",
            }
        ]
    }

    # Mock Checkout Session methods
    mock.checkout.Session.create.return_value = {
        "id": "cs_test123",
        "url": "https://checkout.stripe.com/test_session",
    }

    # Mock Billing Portal methods
    mock.billing_portal.Session.create.return_value = {
        "id": "bps_test123",
        "url": "https://billing.stripe.com/test_session",
    }

    # Mock Subscription delete method
    mock.Subscription.delete.return_value = {
        "id": "sub_test123",
        "status": "canceled",
        "canceled_at": 1729232000,
    }

    # Mock Invoice created event
    mock.Invoice.create.return_value = {
        "id": "inv_test123",
        "amount_due": 5000,
        "currency": "usd",
        "status": "draft",
    }

    # Mock Invoice finalized event
    mock.Invoice.finalize.return_value = {
        "id": "inv_test123",
        "amount_due": 5000,
        "currency": "usd",
        "status": "open",
    }

    # Mock Payment Intent methods
    mock.PaymentIntent.create.return_value = {
        "id": "pi_test123",
        "status": "requires_payment_method",
    }
    mock.PaymentIntent.retrieve.return_value = {
        "id": "pi_test123",
        "status": "succeeded",
    }

    return mock
