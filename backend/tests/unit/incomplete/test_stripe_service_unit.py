# tests/test_stripe_service.py

import pytest
from services.stripe_service import StripeService
from datetime import datetime


@pytest.fixture
def stripe_service(mock_stripe_client):
    return StripeService(mock_stripe_client)


def test_create_customer(stripe_service, mock_stripe_client):
    customer = stripe_service.create_customer("test@example.com")
    assert customer["id"] == "cus_test123"
    assert customer["email"] == "test@example.com"
    mock_stripe_client.Customer.create.assert_called_once_with(email="test@example.com")


def test_create_subscription(stripe_service, mock_stripe_client):
    subscription = stripe_service.create_subscription("cus_test123", "price_test123")
    assert subscription["id"] == "sub_test123"
    assert subscription["status"] == "active"
    mock_stripe_client.Subscription.create.assert_called_once_with(
        customer="cus_test123", items=[{"price": "price_test123"}]
    )


def test_modify_subscription(stripe_service, mock_stripe_client):
    subscription = stripe_service.modify_subscription("sub_test123", "price_test456")
    assert subscription["id"] == "sub_test123"  # Access the 'id' as a dictionary key
    assert subscription["cancel_at_period_end"] is True
    mock_stripe_client.Subscription.modify.assert_called_once_with(
        "sub_test123", items=[{"id": "item_test123", "price": "price_test456"}]
    )


def test_create_checkout_session(stripe_service, mock_stripe_client):
    session = stripe_service.create_checkout_session(
        "test@example.com",
        "cus_test123",
        "price_test123",
        "http://localhost/success",
        "http://localhost/cancel",
    )
    assert session["id"] == "cs_test123"  # Access the 'id' as a dictionary key
    assert session["url"] == "https://checkout.stripe.com/test_session"
    mock_stripe_client.checkout.Session.create.assert_called_once_with(
        payment_method_types=["card"],
        customer="cus_test123",
        line_items=[{"price": "price_test123", "quantity": 1}],
        mode="subscription",
        success_url="http://localhost/success",
        cancel_url="http://localhost/cancel",
        customer_email="test@example.com",
    )


def test_cancel_subscription(stripe_service, mock_stripe_client):
    subscription = stripe_service.cancel_subscription("sub_test123")
    assert subscription["id"] == "sub_test123"
    assert subscription["cancel_at_period_end"] is True
    mock_stripe_client.Subscription.modify.assert_called_once_with(
        "sub_test123", cancel_at_period_end=True
    )


def test_create_billing_portal_session(stripe_service, mock_stripe_client):
    session = stripe_service.create_billing_portal_session(
        "cus_test123", "http://localhost"
    )
    assert session["url"] == "https://billing.stripe.com/test_session"
    mock_stripe_client.billing_portal.Session.create.assert_called_once_with(
        customer="cus_test123", return_url="http://localhost"
    )


def test_retrieve_invoices(stripe_service, mock_stripe_client):
    invoices = stripe_service.retrieve_invoices("cus_test123")
    assert len(invoices["data"]) == 1
    assert invoices["data"][0]["id"] == "inv_test123"
    mock_stripe_client.Invoice.list.assert_called_once_with(customer="cus_test123")


def test_handle_subscription_created(stripe_service, mock_stripe_client, mocker):
    # Mock user lookup and user save
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.save = mocker.MagicMock()

    event_data = {
        "id": "sub_test123",
        "customer": "cus_test123",
        "items": {"data": [{"price": {"id": "price_test123"}}]},
        "current_period_start": 1729145600,  # mock timestamp
        "current_period_end": 1729232000,  # mock timestamp
    }

    stripe_service.handle_subscription_created(event_data)

    # Check if user subscription details were updated and saved
    mock_user.save.assert_called_once()
    assert mock_user.stripe_subscription_id == "sub_test123"
    assert mock_user.subscription_status == "active"
    assert mock_user.cycle_token_limit == 20000  # Default plan cycle token limit


def test_handle_subscription_updated(stripe_service, mock_stripe_client, mocker):
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.save = mocker.MagicMock()

    event_data = {
        "id": "sub_test123",
        "customer": "cus_test123",
        "items": {"data": [{"price": {"id": "price_test123"}}]},
        "current_period_end": 1729232000,  # mock timestamp
        "status": "active",
        "cancel_at_period_end": False,
    }

    stripe_service.handle_subscription_updated(event_data)

    mock_user.save.assert_called_once()
    assert mock_user.subscription_status == "active"
    assert mock_user.subscription_end_date == datetime.utcfromtimestamp(1729232000)


def test_handle_checkout_session(stripe_service, mock_stripe_client, mocker):
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.stripe_customer_id = None  # Set initial value before it's updated
    mock_user.stripe_subscription_id = None
    mock_user.subscription_status = None
    mock_user.save = mocker.MagicMock()

    session_data = {
        "customer": "cus_test123",
        "subscription": "sub_test123",
        "customer_email": "test@example.com",
    }

    stripe_service.handle_checkout_session(session_data)

    mock_user.save.assert_called_once()
    assert mock_user.stripe_customer_id == "cus_test123"
    assert mock_user.stripe_subscription_id == "sub_test123"
    assert mock_user.subscription_status == "active"


def test_handle_invoice_payment(stripe_service, mock_stripe_client, mocker):
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.save = mocker.MagicMock()

    invoice_data = {"customer": "cus_test123"}

    stripe_service.handle_invoice_payment(invoice_data)

    mock_user.save.assert_called_once()
    assert mock_user.subscription_status == "active"
    assert mock_user.has_failed_payment is False


def test_handle_payment_failure(stripe_service, mock_stripe_client, mocker):
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.save = mocker.MagicMock()

    event_data = {"customer": "cus_test123"}

    stripe_service.handle_payment_failure(event_data)

    mock_user.save.assert_called_once()
    assert mock_user.subscription_status == "past_due"
    assert mock_user.has_failed_payment is True


def test_handle_subscription_deleted(stripe_service, mock_stripe_client, mocker):
    mock_user = mocker.patch("models.user.User.objects").return_value.first.return_value
    mock_user.save = mocker.MagicMock()

    event_data = {"id": "sub_test123", "customer": "cus_test123"}

    stripe_service.handle_subscription_deleted(event_data)

    mock_user.save.assert_called_once()
    assert mock_user.subscription_status == "inactive"
