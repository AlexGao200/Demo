from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from models.user import User
from models.organization import Organization
from models.user_organization import UserOrganization
from loguru import logger
from auth.utils import token_required
from datetime import datetime
from bson import ObjectId
import stripe
from flask import current_app
import os


def create_subscriptions_blueprint(stripe_service):
    subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/api")

    @subscriptions_bp.route("/webhook", methods=["POST"])
    def stripe_webhook():
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get("Stripe-Signature")
        endpoint_secret = (
            "whsec_PVznbwNLsyQ5cECaiizoAiiWUpa6W3Oq"  # Use your actual secret
        )

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except stripe.error.SignatureVerificationError as e:
            return jsonify({"error": str(e)}), 400

        event_type = event.get("type")
        event_data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            stripe_service.handle_checkout_session(event_data)
        elif event_type == "invoice.payment_succeeded":
            stripe_service.handle_invoice_payment(event_data)
        elif event_type == "customer.subscription.created":
            stripe_service.handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            stripe_service.handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            stripe_service.handle_subscription_deleted(event_data)
        elif event_type == "payment_intent.succeeded":
            stripe_service.handle_payment_intent_succeeded(event_data)
        elif event_type == "payment_intent.created":
            stripe_service.handle_payment_intent_created(event_data)
        elif event_type == "invoice.created":
            stripe_service.handle_invoice_created(event_data)
        elif event_type == "invoice.finalized":
            stripe_service.handle_invoice_finalized(event_data)
        else:
            logger.warning(f"Unhandled event type: {event_type}")

        return jsonify({"status": "success"}), 200

    @subscriptions_bp.route("/products", methods=["GET"])
    def get_products():
        try:
            # Fetch products and prices via StripeService
            logger.info("Attempting to fetch products and prices from Stripe")
            products = stripe_service.get_active_products_with_prices()

            # Return product details as JSON
            return jsonify(products), 200
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")  # Log the exact error
            return jsonify({"error": "Unable to fetch products"}), 500

    @subscriptions_bp.route("/billing-portal", methods=["GET"])
    @cross_origin(
        origins=[
            "http://localhost:3000",
            "http://a230ce07d73f043fca905767a3d01f92-1101156471.us-west-1.elb.amazonaws.com",
        ],
        supports_credentials=True,
    )
    @token_required
    def billing_portal(current_user):
        try:
            if not current_user.stripe_customer_id:
                return (
                    jsonify(
                        {"error": "no_customer_id", "message": "User is not subscribed"}
                    ),
                    400,
                )
            FRONTEND_URL = os.getenv(
                "FRONTEND_BASE_URL", "http://localhost:3000"
            )  # Default to localhost in dev
            # Use the injected service to create the billing portal session
            session = stripe_service.create_billing_portal_session(
                current_user.stripe_customer_id,
                return_url=f"{FRONTEND_URL}/subscription-management",
            )
            return jsonify({"url": session.url}), 200

        except Exception as e:
            logger.error(f"Error creating billing portal session: {e}")
            return jsonify({"error": "Error creating billing portal session"}), 500

    @subscriptions_bp.route("/subscribe", methods=["POST"])
    @token_required
    def create_subscription(current_user):
        try:
            data = request.get_json()
            plan_id = data.get("plan_id")

            if not plan_id:
                return jsonify({"error": "Plan ID is required"}), 400

            if not current_user.stripe_customer_id:
                customer = stripe_service.create_customer(current_user.email)
                current_user.stripe_customer_id = customer.id
                current_user.save()

            subscription = stripe_service.create_subscription(
                current_user.stripe_customer_id, plan_id
            )

            current_user.subscription_status = "active"
            current_user.stripe_subscription_id = subscription.id
            current_user.save()

            return jsonify({"message": "Subscription created successfully."}), 200

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/subscription_update", methods=["POST"])
    @token_required
    def update_subscription(current_user):
        try:
            data = request.get_json()
            new_plan_id = data.get("new_plan_id")

            if not new_plan_id:
                return jsonify({"error": "New plan ID is required"}), 400

            if not current_user.stripe_subscription_id:
                return jsonify({"error": "No active subscription found"}), 404

            # Call to StripeService to modify the subscription
            stripe_service.modify_subscription(
                current_user.stripe_subscription_id, new_plan_id
            )

            # Fetch the product name from Stripe and update user details
            new_price = stripe_service.stripe_client.Price.retrieve(new_plan_id)
            new_product = stripe_service.stripe_client.Product.retrieve(
                new_price["product"]
            )

            current_user.subscription_status = "active"
            current_user.subscription_plan_name = new_product[
                "name"
            ]  # Update the product plan name
            current_user.cycle_token_limit = (
                10000  # Example: Update based on the new plan
            )
            current_user.save()

            return jsonify({"message": "Subscription updated successfully."}), 200

        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/subscription_cancel", methods=["POST"])
    @token_required
    def cancel_subscription(current_user):
        try:
            if not current_user.stripe_subscription_id:
                return jsonify({"error": "No active subscription found"}), 404

            # Cancel at the end of the current billing period
            subscription = stripe_service.cancel_subscription(
                current_user.stripe_subscription_id
            )

            # Update the user status to indicate cancellation at period end
            current_user.subscription_status = "cancel_at_period_end"
            current_user.subscription_end_date = datetime.fromtimestamp(
                subscription["current_period_end"]
            )  # Stripe timestamp
            current_user.save()

            return (
                jsonify(
                    {
                        "message": "Subscription canceled successfully.",
                        "subscription_end_date": current_user.subscription_end_date,  # Return to frontend
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/invoices", methods=["GET"])
    @token_required
    def get_invoices(current_user):
        try:
            invoices = stripe_service.retrieve_invoices(current_user.stripe_customer_id)
            return jsonify([invoice for invoice in invoices["data"]]), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/create-checkout-session", methods=["POST"])
    @token_required
    def create_checkout_session(current_user):
        try:
            data = request.get_json()
            price_id = data.get("price_id")

            logger.info(
                f"Received request to create checkout session for user {current_user.email} with price_id: {price_id}"
            )

            if not price_id:
                return jsonify({"error": "Price ID is required"}), 400

            # Create a Checkout Session for the selected price
            logger.info("Creating checkout session...")
            FRONTEND_URL = os.getenv(
                "FRONTEND_BASE_URL", "http://localhost:3000"
            )  # Default to localhost in dev
            checkout_session = stripe_service.create_checkout_session(
                current_user.email,
                current_user.stripe_customer_id,
                price_id,
                success_url=f"{FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/cancel",
            )

            # Ensure that we get a valid session ID
            if checkout_session and "id" in checkout_session:
                logger.info(
                    f"Checkout session created successfully with ID: {checkout_session['id']}"
                )
                return jsonify({"id": checkout_session["id"]}), 200
            else:
                logger.error(
                    f"Checkout session creation failed or returned an unexpected response: {checkout_session}"
                )
                return jsonify({"error": "Checkout session creation failed"}), 500

        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            return jsonify({"error": str(e)}), 500

    ### Organizational subscription routes
    @subscriptions_bp.route("/manage_user_subscription", methods=["POST"])
    @token_required
    def manage_user_subscription(current_user):
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
        try:
            data = request.get_json()
            org_id = data.get("org_uuid")
            user_id = data.get("user_id")
            new_status = data.get(
                "subscription_status"
            )  # Expected values: "active", "inactive"

            # Validate input
            if not org_id or not user_id or not new_status:
                return (
                    jsonify(
                        {
                            "error": "Organization ID, user ID, and subscription status are required"
                        }
                    ),
                    400,
                )

            if new_status not in ["active", "inactive"]:
                return (
                    jsonify(
                        {
                            "error": "Invalid subscription status. Must be 'active' or 'inactive'"
                        }
                    ),
                    400,
                )

            # Check if org_id is a valid ObjectId
            if not ObjectId.is_valid(org_id):
                return jsonify({"error": "Invalid organization ID format"}), 400

            # Find the organization by its ObjectId
            organization = Organization.objects(id=ObjectId(org_id)).first()
            if not organization:
                return jsonify({"error": "Organization not found"}), 404

            # Get the current user's role in the organization
            user_role = UserOrganization.get_user_role_in_organization(
                current_user.id, ObjectId(org_id)
            )
            if not user_role or user_role != "admin":
                return (
                    jsonify(
                        {
                            "error": "Unauthorized. Only administrators can manage user subscriptions"
                        }
                    ),
                    403,
                )

            # Find the user by their ID
            user = User.objects(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Handle user's Stripe subscription if necessary
            if new_status == "active" and user.stripe_subscription_id:
                try:
                    # Cancel the user's personal Stripe subscription
                    stripe.Subscription.modify(
                        user.stripe_subscription_id,
                        cancel_at_period_end=True,  # Cancels at the end of the current billing period
                    )
                    user.stripe_subscription_id = (
                        None  # Clear the Stripe subscription ID after cancellation
                    )
                except Exception as e:
                    logger.error(f"Error canceling user's subscription: {e}")
                    return (
                        jsonify(
                            {"error": "Error canceling user's individual subscription"}
                        ),
                        500,
                    )

            # Change the user's subscription status based on the organization's decision
            if new_status == "active":
                user.subscription_paid_by = organization  # Set organization as the one paying for the subscription
                user.subscription_status = "active"
                organization.add_paid_member(user)
            elif new_status == "inactive":
                user.subscription_paid_by = (
                    None  # Clear the organization paying for the subscription
                )
                user.subscription_status = "inactive"
                organization.remove_paid_member(user)

            user.save()

            return (
                jsonify(
                    {"message": f"User subscription status changed to {new_status}"}
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error managing user subscription: {e}")
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/organization/set_user_token_limit", methods=["POST"])
    @token_required
    def set_user_token_limit(current_user):
        try:
            data = request.get_json()
            org_uuid = data.get("org_uuid")
            user_id = data.get("user_id")
            token_limit = data.get("token_limit")

            if not org_uuid or not user_id or token_limit is None:
                return (
                    jsonify(
                        {
                            "error": "Organization UUID, user ID, and token limit are required"
                        }
                    ),
                    400,
                )

            if token_limit < 0:
                return (
                    jsonify({"error": "Token limit must be a non-negative integer"}),
                    400,
                )

            # Find the organization by its UUID
            organization = Organization.objects(uuid=org_uuid).first()
            if not organization:
                return jsonify({"error": "Organization not found"}), 404

            # Retrieve the current user's role in the organization
            user_role = UserOrganization.get_user_role_in_organization(
                current_user.id, organization.id
            )
            if not user_role or user_role != "admin":
                return (
                    jsonify(
                        {
                            "error": "Unauthorized. Only administrators can set token limits for users"
                        }
                    ),
                    403,
                )

            # Find the target user by their ID
            user = User.objects(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Set the token limit for the user
            user.set_token_limit(int(token_limit))

            return (
                jsonify(
                    {
                        "message": f"Token limit set to {token_limit} for user {user.first_name} {user.last_name}"
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error setting user token limit: {e}")
            return jsonify({"error": str(e)}), 500

    @subscriptions_bp.route("/organization/remove_user_token_limit", methods=["POST"])
    @token_required
    def remove_user_token_limit(current_user):
        try:
            data = request.get_json()
            org_uuid = data.get("org_uuid")
            user_id = data.get("user_id")

            if not org_uuid or not user_id:
                return (
                    jsonify({"error": "Organization UUID and user ID are required"}),
                    400,
                )

            # Find the organization by its UUID
            organization = Organization.objects(uuid=org_uuid).first()
            if not organization:
                return jsonify({"error": "Organization not found"}), 404

            # Retrieve the current user's role in the organization
            user_role = UserOrganization.get_user_role_in_organization(
                current_user.id, organization.id
            )
            if not user_role or user_role != "admin":
                return (
                    jsonify(
                        {
                            "error": "Unauthorized. Only administrators can remove token limits for users"
                        }
                    ),
                    403,
                )

            # Find the target user by their ID
            user = User.objects(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Remove the token limit for the user
            user.clear_token_limit()

            return (
                jsonify(
                    {
                        "message": f"Token limit removed for user {user.first_name} {user.last_name}"
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error removing user token limit: {e}")
            return jsonify({"error": str(e)}), 500

    return subscriptions_bp
