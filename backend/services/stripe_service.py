import stripe
from loguru import logger
from models.user import User
from datetime import datetime, timezone


class StripeService:
    def __init__(self, stripe_client):
        self.stripe_client = stripe_client

    # Create Customer
    def create_customer(self, email):
        return self.stripe_client.Customer.create(email=email)

    # Create Subscription
    def create_subscription(self, customer_id, plan_id):
        return self.stripe_client.Subscription.create(
            customer=customer_id, items=[{"price": plan_id}]
        )

    # Modify Subscription
    def modify_subscription(self, subscription_id, plan_id):
        subscription = self.stripe_client.Subscription.retrieve(subscription_id)
        item_id = subscription["items"]["data"][0]["id"]  # Fixed this line
        return self.stripe_client.Subscription.modify(
            subscription_id, items=[{"id": item_id, "price": plan_id}]
        )

    # Cancel Subscription
    def cancel_subscription(self, subscription_id):
        """Cancels the subscription at the end of the billing period."""
        try:
            subscription = self.stripe_client.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,  # Cancels at the end of the current billing period
            )
            return (
                subscription  # Return the subscription object with current_period_end
            )
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription in Stripe: {e}")
            raise e

    # Billing Portal
    def create_billing_portal_session(self, customer_id, return_url):
        return self.stripe_client.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )

    # Retrieve Invoices
    def retrieve_invoices(self, customer_id):
        return self.stripe_client.Invoice.list(customer=customer_id)

    # Create Checkout Session
    def create_checkout_session(
        self, customer_email, customer_id, price_id, success_url, cancel_url
    ):
        """Creates a checkout session for a customer with a specific price."""
        try:
            logger.info(
                f"Creating a checkout session for customer {customer_email} with price_id {price_id}"
            )

            # Step 1: Check if the provided customer_id exists in Stripe
            customer = None
            if customer_id:
                try:
                    customer = self.stripe_client.Customer.retrieve(customer_id)
                except stripe.error.InvalidRequestError as e:
                    logger.warning(
                        f"Customer with ID {customer_id} not found. Error: {e}"
                    )
                    customer = None

            # Step 2: If no valid customer, create a new one
            if not customer or not customer.get("id"):
                customer = self.stripe_client.Customer.create(email=customer_email)
                customer_id = customer.id

            # Step 3: Create the checkout session
            # Only pass `customer_email` if no customer exists, otherwise pass `customer`
            session_params = {
                "payment_method_types": ["card"],
                "line_items": [
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
            }

            if customer_id:
                session_params["customer"] = customer_id  # Use existing customer
            else:
                session_params["customer_email"] = (
                    customer_email  # Use email to create a new customer
                )

            session = self.stripe_client.checkout.Session.create(**session_params)

            logger.info(f"Checkout session created successfully with ID: {session.id}")
            return session

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe API error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    # Get active products and prices
    def get_active_products_with_prices(self):
        """Fetches active products and their associated prices from Stripe."""
        try:
            product_details = []
            has_more = True
            starting_after = None

            # Paginate through all active prices
            while has_more:
                prices = self.stripe_client.Price.list(
                    active=True, starting_after=starting_after
                )
                for price in prices["data"]:
                    product_id = price["product"]
                    product = self.stripe_client.Product.retrieve(product_id)

                    # Only include active products
                    if not product["active"]:
                        continue  # Skip this product if it's inactive

                    # Handle recurring pricing information
                    recurring_info = price.get("recurring")
                    recurring_interval = (
                        recurring_info.get("interval", "one-time")
                        if recurring_info
                        else "one-time"
                    )

                    # Add product and price details to the list
                    product_details.append(
                        {
                            "product_id": product["id"],
                            "product_name": product["name"],
                            "price_id": price["id"],
                            "unit_amount": price["unit_amount"]
                            / 100,  # Convert from cents to dollars
                            "currency": price["currency"].upper(),
                            "recurring": recurring_interval,
                        }
                    )

                # Handle pagination
                has_more = prices["has_more"]
                if has_more:
                    starting_after = prices["data"][-1]["id"]  # Move to the next page

            return product_details

        except Exception as e:
            logger.error(f"Error fetching products from Stripe: {e}")
            raise Exception(f"Error fetching products: {str(e)}")

    # Handle Payment Intent Succeeded
    def handle_payment_intent_succeeded(self, event_data):
        """Handle when a payment intent has succeeded."""
        logger.info(
            f"Payment intent succeeded for payment intent ID: {event_data.get('id')}"
        )

    # Handle Payment Intent Created
    def handle_payment_intent_created(self, event_data):
        """Handle when a payment intent is created."""
        logger.info(f"Payment intent created for ID: {event_data.get('id')}")

    # Handle Invoice Created
    def handle_invoice_created(self, event_data):
        """Handle when an invoice is created."""
        logger.info(f"Invoice created for ID: {event_data.get('id')}")

    # Handle Invoice Finalized
    def handle_invoice_finalized(self, event_data):
        """Handle when an invoice is finalized."""
        logger.info(f"Invoice finalized for ID: {event_data.get('id')}")

    def handle_invoice_payment(self, invoice_data):
        """Handles the successful payment of a Stripe invoice."""
        customer_id = invoice_data["customer"]
        user = User.objects(stripe_customer_id=customer_id).first()

        if not user:
            # Fetch customer email from Stripe if the user is not found
            customer_obj = self.stripe_client.Customer.retrieve(customer_id)
            customer_email = customer_obj.get("email")

            if customer_email:
                user = User.objects(email=customer_email).first()

        if user:
            user.subscription_status = "active"
            user.has_failed_payment = False
            user.save()
            logger.info(f"Invoice payment succeeded for user {user.email}.")
        else:
            logger.error(
                f"No user found with Stripe customer ID {customer_id} for invoice payment."
            )

    # Handle Subscription Created Event
    def handle_subscription_created(self, event_data):
        """Handles the event when a subscription is created."""
        try:
            subscription_id = event_data.get("id")
            customer_id = event_data.get("customer")

            # Check if event_data contains price information
            price_data = event_data["items"]["data"][0].get("price", {})
            price_id = price_data.get("id")

            if not price_id:
                logger.error(
                    f"No price ID found in event data for subscription {subscription_id}"
                )
                return

            # Fetch the associated product and price information
            price = self.stripe_client.Price.retrieve(price_id)
            product = self.stripe_client.Product.retrieve(price["product"])
            plan_name = product["name"]  # Get product name from Stripe

            # Handle subscription period start/end times
            current_period_start = datetime.utcfromtimestamp(
                event_data["current_period_start"]
            )
            current_period_end = datetime.utcfromtimestamp(
                event_data["current_period_end"]
            )

            # Try to find the user by customer_id first
            user = User.objects(stripe_customer_id=customer_id).first()

            # If user is not found by customer_id, fetch the customer details from Stripe
            if not user:
                customer_obj = self.stripe_client.Customer.retrieve(customer_id)
                customer_email = customer_obj.get("email")

                if customer_email:
                    user = User.objects(email=customer_email).first()
                    logger.info(
                        f"User lookup by email {customer_email} after fetching customer details from Stripe."
                    )

            if user:
                # Update the user's subscription details
                user.stripe_subscription_id = subscription_id
                user.subscription_status = "active"
                user.subscription_plan_name = plan_name  # Store the product name
                user.subscription_start_date = current_period_start
                user.subscription_end_date = current_period_end

                # Set plan-specific features, such as cycle_token_limit (adjust based on plan if necessary)
                if "Pro Plan" in plan_name:
                    user.cycle_token_limit = 20000  # Example for a Pro plan
                elif "Basic Plan" in plan_name:
                    user.cycle_token_limit = 10000  # Example for a Basic plan
                else:
                    user.cycle_token_limit = 5000  # Default plan cycle token limit

                user.current_cycle_message_count = (
                    0  # Reset message count for the new subscription
                )
                user.has_failed_payment = False
                user.save()

                logger.info(
                    f"Subscription created for user {user.email}, subscription ID: {subscription_id}, plan: {plan_name}"
                )
            else:
                logger.error(
                    f"No user found for customer ID: {customer_id} or email {customer_email if customer_email else 'N/A'}"
                )

        except Exception as e:
            logger.error(f"Error handling subscription created event: {e}")
            raise

    # Handle Subscription Updated Event
    def handle_subscription_updated(self, event_data):
        """Handles updates to an existing subscription."""
        subscription_id = event_data.get("id")
        customer_id = event_data.get("customer")
        price_id = event_data["items"]["data"][0]["price"]["id"]

        # Fetch the associated product and price information
        price = self.stripe_client.Price.retrieve(price_id)
        product = self.stripe_client.Product.retrieve(price["product"])
        plan_name = product["name"]  # Get product name from Stripe

        current_period_end = datetime.utcfromtimestamp(event_data["current_period_end"])
        status = event_data.get("status")
        cancel_at_period_end = event_data.get("cancel_at_period_end", False)

        # Find the user by Stripe customer ID
        user = User.objects(stripe_customer_id=customer_id).first()

        if user:
            user.stripe_subscription_id = subscription_id
            user.subscription_plan_name = plan_name  # Store the product name
            user.subscription_status = status
            user.subscription_end_date = current_period_end

            # If the subscription is set to cancel at the end of the period
            if cancel_at_period_end:
                user.subscription_status = "cancel_at_period_end"
                user.subscription_end_date = current_period_end  # Save the end date

            user.save()

            logger.info(
                f"Subscription updated for user {user.email}, subscription ID: {subscription_id}, plan: {plan_name}, status: {status}"
            )
        else:
            logger.error(f"No user found for customer ID: {customer_id}")

    # Handle Subscription Deleted
    def handle_subscription_deleted(self, event_data):
        """Handle when a subscription is fully canceled (end of billing period)."""
        subscription_id = event_data.get("id")
        customer_id = event_data.get("customer")

        user = User.objects(stripe_customer_id=customer_id).first()

        if user:
            # Mark the subscription as inactive or canceled
            user.subscription_status = "inactive"
            user.save()

            logger.info(
                f"Subscription deleted for user {user.email}. Subscription ID: {subscription_id}"
            )

    # Handle Checkout Session Completion
    def handle_checkout_session(self, session_data):
        """Handles the completion of a Stripe checkout session."""
        customer_id = session_data.get("customer")
        subscription_id = session_data.get("subscription")
        customer_email = session_data.get("customer_email") or session_data.get(
            "customer_details", {}
        ).get("email")

        # Try to find the user by customer_id first
        user = User.objects(stripe_customer_id=customer_id).first()

        # If user is not found by customer_id, fall back to email lookup
        if not user and customer_email:
            user = User.objects(email=customer_email).first()

        if user:
            # Ensure both stripe_customer_id and email are saved for future webhook events
            if not user.stripe_customer_id:
                user.stripe_customer_id = customer_id

            if not user.email:
                user.email = customer_email

            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active"
            user.subscription_start_date = datetime.now(timezone.utc)
            user.save()

            logger.info(
                f"Updated user {user.email} with subscription status 'active', customer_id: {customer_id}, subscription_id: {subscription_id}."
            )
        else:
            logger.error(
                f"User not found by email: {customer_email} or customer_id: {customer_id} for checkout session."
            )

    # Handle Payment Failure
    def handle_payment_failure(self, event_data):
        """Handle payment failures."""
        customer_id = event_data["customer"]
        user = User.objects(stripe_customer_id=customer_id).first()

        if user:
            user.has_failed_payment = True
            user.subscription_status = "past_due"
            user.save()
            logger.warning(
                f"Payment failure for user {user.email}, marked as past_due."
            )
        else:
            logger.error(
                f"Payment failure event received for unknown customer ID: {customer_id}"
            )
