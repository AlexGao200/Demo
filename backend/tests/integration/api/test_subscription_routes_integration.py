import json
from unittest.mock import patch

valid_price_id = "price_1QASZFRtAgEFTutZLDB7nKlI"


# Test POST /api/subscribe
def test_create_subscription(client, mock_stripe_service, auth_headers):
    mock_stripe_service.create_customer.return_value = {"id": "cus_test123"}
    mock_stripe_service.create_subscription.return_value = {
        "id": "sub_test123",
        "status": "active",
    }

    url = "/api/subscribe"

    # Simulate a subscription request
    response = client.post(
        url,
        json={
            "plan_id": "price_test123"
        },  # Replace with a valid price_id from your Stripe test environment
        headers=auth_headers,
    )

    # Assert response is successful
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data["message"] == "Subscription created successfully."
    mock_stripe_service.create_customer.assert_called_once()
    mock_stripe_service.create_subscription.assert_called_once_with(
        "cus_test123", "price_test123"
    )


# Test POST /api/webhook (stripe webhook handler)
@patch(
    "stripe.Webhook.construct_event",
    return_value={"type": "checkout.session.completed", "data": {"object": {}}},
)
def test_stripe_webhook_checkout_session_completed(client, mock_construct_event):
    url = "/api/webhook"
    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "customer_email": "test@example.com",
            }
        },
    }

    # Send the POST request
    response = client.post(
        url,
        data=json.dumps(event_data),
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": "mock_signature",
        },
    )

    # Assert that the webhook was processed successfully
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data["status"] == "success"


# Test POST /api/subscription_update
def test_update_subscription(client, mock_stripe_service, auth_headers):
    mock_stripe_service.modify_subscription.return_value = {
        "id": "sub_test123",
        "status": "active",
    }

    url = "/api/subscription_update"
    response = client.post(
        url, json={"new_plan_id": valid_price_id}, headers=auth_headers
    )

    # Assert response is successful
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}. Response: {response.text}"
    mock_stripe_service.modify_subscription.assert_called_once_with(
        "sub_test123", valid_price_id
    )


# Test POST /api/subscription_cancel
def test_cancel_subscription(client, mock_stripe_service, auth_headers):
    mock_stripe_service.cancel_subscription.return_value = {
        "id": "sub_test123",
        "current_period_end": 1729232000,
    }

    url = "/api/subscription_cancel"
    response = client.post(url, headers=auth_headers)

    # Assert response is successful
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}. Response: {response.text}"
    mock_stripe_service.cancel_subscription.assert_called_once_with("sub_test123")


# Test GET /api/products
def test_get_products(client, mock_stripe_service, auth_headers):
    mock_stripe_service.get_active_products_with_prices.return_value = [
        {
            "product_id": "prod_test123",
            "price_id": "price_test123",
            "unit_amount": 10000,
            "currency": "USD",
            "recurring": "monthly",
        }
    ]

    url = "/api/products"
    response = client.get(url, headers=auth_headers)

    # Assert response is successful
    assert (
        response.status_code == 200
    ), f"Unexpected status code: {response.status_code}. Response: {response.text}"
    data = response.json()
    assert len(data) > 0, f"Expected non-empty products list, got: {data}"
    product_id = data[0]["product_id"]
    assert product_id.startswith("prod_")  # Check that it's a valid product ID
    mock_stripe_service.get_active_products_with_prices.assert_called_once()
