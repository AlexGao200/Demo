from datetime import timedelta
from flask import (
    Blueprint,
    request,
    jsonify,
    redirect,
    current_app,
    make_response,
    session,
)
import jwt
from loguru import logger
from auth.utils import get_token
from services.auth_service import (
    AuthService,
    RegistrationData,
    LoginData,
    AuthError,
    RegistrationError,
    LoginError,
    TokenError,
)
from services.email_service import EmailService
from services.organization_service import OrganizationService
from services.user_service import UserService
from services.guest_services import GuestSessionManager
from auth.utils import generate_token, decode_token

# test. remove me


def handle_cors_options():
    """Handle CORS OPTIONS requests by setting appropriate headers.

    Returns:
        Response: A Flask response object with CORS headers set.
    """
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin"))
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


def create_auth_blueprint(
    auth_service: AuthService,
    email_service: EmailService,
    organization_service: OrganizationService,
    user_service: UserService,
):
    auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

    @auth_bp.route("/register", methods=["POST", "OPTIONS"])
    def register_user():
        if request.method == "OPTIONS":
            return handle_cors_options()

        logger.info("Received a registration request.")
        data = request.get_json()

        if not data:
            logger.warning("No input data provided")
            return jsonify({"message": "No input data provided"}), 400

        try:
            registration_data = RegistrationData(
                email=data.get("email", "").strip().lower(),
                first_name=data.get("first_name", "").strip(),
                last_name=data.get("last_name", "").strip(),
                username=data.get("username", "").strip().lower(),
                password=data.get("password"),
                invitation_token=data.get("invitation_token"),
                organization_registration_code=data.get(
                    "organization_registration_code"
                ),
            )

            # Complete the basic registration
            user, org_name = auth_service.complete_registration(registration_data)

            # Create user's personal index
            personal_index = user_service.create_user_index(user)
            if not personal_index:
                logger.warning(
                    f"Failed to create personal index for user {user.username}"
                )

            # If there's an organization registration code, handle organization membership
            if registration_data.organization_registration_code:
                try:
                    # The organization service will validate the code and assign proper membership
                    organization_service.manage_member(
                        organization_id=org_name,  # org_name here is actually org_id from complete_registration
                        user=user,
                        role="member",  # Default role for new registrations
                        actor=None,  # No actor as this is part of registration
                    )
                except ValueError as e:
                    logger.warning(f"Organization membership error: {str(e)}")
                    # We don't fail the registration if org assignment fails
                    # but we should log it and return it in the response
                    return jsonify(
                        {
                            "message": "User registered successfully but organization assignment failed.",
                            "org_error": str(e),
                        }
                    ), 201

            return (
                jsonify(
                    {
                        "message": "User registered successfully.",
                        "org_name_to_show_user": org_name,
                    }
                ),
                201,
            )

        except RegistrationError as e:
            logger.warning(f"Registration error: {str(e)}")
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

    @auth_bp.route("/refresh_token", methods=["POST", "OPTIONS"])
    def refresh_token():
        logger.info("Refresh token endpoint called")

        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            # Log incoming token sources
            refresh_token = request.json.get("refresh_token") or request.cookies.get(
                "refresh_token"
            )
            logger.info(
                f"Token source - JSON: {bool(request.json.get('refresh_token'))}, Cookie: {bool(request.cookies.get('refresh_token'))}"
            )

            if not refresh_token:
                logger.info("No refresh token provided, creating new guest session")
                guest_manager = GuestSessionManager()
                guest_user, session_id = guest_manager.get_or_create_guest_session()
                logger.info(f"Created new guest session with ID: {session_id}")

                new_token = generate_token(
                    {
                        "id": str(guest_user.id),
                        "is_guest": True,
                        "session_id": session_id,
                    },
                    expires_in=timedelta(hours=24),
                )
                user_data = {
                    "id": str(guest_user.id),
                    "is_guest": True,
                    "session_id": session_id,
                }
                logger.info(f"Generated new guest token for session: {session_id}")

                response = make_response(
                    jsonify(
                        {"access_token": new_token, "user": user_data, "is_guest": True}
                    ),
                    200,
                )
                response.set_cookie("token", new_token, httponly=True)
                return response

            # Try to decode the refresh token
            try:
                logger.debug("Attempting to decode refresh token")
                decoded = decode_token(refresh_token)
                user_id = decoded.get("user_id")
                is_guest = decoded.get("is_guest", False)

                logger.info(f"Decoded token - User ID: {user_id}, Is Guest: {is_guest}")

                if is_guest:
                    logger.info("Processing guest token refresh")
                    session_id = decoded.get("session_id")
                    logger.debug(f"Guest session ID: {session_id}")

                    guest_manager = GuestSessionManager()
                    guest_user = guest_manager.get_or_create_guest_session(session_id)[
                        0
                    ]
                    logger.info(f"Retrieved guest user for session: {session_id}")

                    new_token = generate_token(
                        {
                            "id": str(guest_user.id),
                            "is_guest": True,
                            "session_id": session_id,
                        },
                        expires_in=timedelta(hours=24),
                    )
                    user_data = {
                        "id": str(guest_user.id),
                        "is_guest": True,
                        "session_id": session_id,
                    }
                else:
                    logger.info(
                        f"Processing regular user token refresh for user: {user_id}"
                    )
                    try:
                        user_data, new_token = auth_service.refresh_token(refresh_token)
                        logger.info(f"Successfully refreshed token for user: {user_id}")
                    except TokenError as e:
                        logger.warning(
                            f"Token refresh failed for user {user_id}: {str(e)}"
                        )
                        # Create new guest session if user not found
                        logger.info("Falling back to guest session creation")
                        guest_manager = GuestSessionManager()
                        guest_user, session_id = (
                            guest_manager.get_or_create_guest_session()
                        )
                        logger.info(f"Created fallback guest session: {session_id}")

                        new_token = generate_token(
                            {
                                "id": str(guest_user.id),
                                "is_guest": True,
                                "session_id": session_id,
                            },
                            expires_in=timedelta(hours=24),
                        )
                        user_data = {
                            "id": str(guest_user.id),
                            "is_guest": True,
                            "session_id": session_id,
                        }
                        is_guest = True

                response = make_response(
                    jsonify(
                        {
                            "access_token": new_token,
                            "user": user_data,
                            "is_guest": is_guest,
                        }
                    ),
                    200,
                )
                response.set_cookie("token", new_token, httponly=True)
                logger.info("Successfully generated response with new token")
                return response

            except jwt.ExpiredSignatureError:
                logger.warning("Token expired, creating new guest session")
                guest_manager = GuestSessionManager()
                guest_user, session_id = guest_manager.get_or_create_guest_session()
                logger.info(
                    f"Created new guest session after token expiration: {session_id}"
                )

                new_token = generate_token(
                    {
                        "id": str(guest_user.id),
                        "is_guest": True,
                        "session_id": session_id,
                    },
                    expires_in=timedelta(hours=24),
                )
                user_data = {
                    "id": str(guest_user.id),
                    "is_guest": True,
                    "session_id": session_id,
                }

                response = make_response(
                    jsonify(
                        {"access_token": new_token, "user": user_data, "is_guest": True}
                    ),
                    200,
                )
                response.set_cookie("token", new_token, httponly=True)
                return response

        except Exception as e:
            logger.error(
                f"Unexpected error in refresh_token endpoint: {str(e)}", exc_info=True
            )
            return jsonify({"error": "An unexpected error occurred"}), 500

    @auth_bp.route("/initiate-registration", methods=["POST", "OPTIONS"])
    def initiate_registration():
        if request.method == "OPTIONS":
            return handle_cors_options()

        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"message": "Email is required"}), 400

        try:
            auth_service.initiate_registration(email)
            return jsonify({"message": "Verification email sent"}), 200
        except RegistrationError as e:
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to initiate registration: {str(e)}")
            return jsonify({"message": "Internal Server Error"}), 500

    @auth_bp.route("/verify-email-code", methods=["POST", "OPTIONS"])
    def verify_email_code():
        if request.method == "OPTIONS":
            return handle_cors_options()

        data = request.get_json()
        email = data.get("email")
        code = data.get("code")

        if not email or not code:
            return jsonify({"message": "Email and verification code are required"}), 400

        try:
            if auth_service.verify_email_with_code(email, code):
                return jsonify({"message": "Email verified successfully"}), 200
            return jsonify({"message": "Invalid verification code"}), 400
        except RegistrationError as e:
            return jsonify({"message": str(e)}), 400

    @auth_bp.route("/verify-email/<token>", methods=["GET", "OPTIONS"])
    def verify_email(token):
        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            success, email = auth_service.verify_email_with_token(token)
            if success:
                return redirect(
                    f"{current_app.config['FRONTEND_BASE_URL']}/register?verification=success&email={email}"
                )
            return redirect(
                f"{current_app.config['FRONTEND_BASE_URL']}/register?verification=failed&error=invalid_token"
            )
        except RegistrationError as e:
            logger.error(f"Error during email verification: {str(e)}")
            error_type = (
                "expired_token" if "expired" in str(e).lower() else "server_error"
            )
            return redirect(
                f"{current_app.config['FRONTEND_BASE_URL']}/register?verification=failed&error={error_type}"
            )

    @auth_bp.route("/resend-verification", methods=["POST", "OPTIONS"])
    def resend_verification():
        if request.method == "OPTIONS":
            return handle_cors_options()

        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"message": "Email is required"}), 400

        try:
            auth_service.initiate_registration(email)
            return jsonify({"message": "Verification email resent"}), 200
        except RegistrationError as e:
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to resend verification: {str(e)}")
            return jsonify({"message": "Internal Server Error"}), 500

    @auth_bp.route("/login", methods=["POST", "OPTIONS"])
    def login_user():
        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            data = request.get_json()
            if not data:
                return jsonify({"message": "No input data provided"}), 400

            email_or_username = data.get("usernameOrEmail")
            password = data.get("password")

            if not email_or_username or not password:
                return jsonify(
                    {"message": "Username/email and password are required"}
                ), 400

            login_data = LoginData(
                email_or_username=email_or_username,
                password=password,
            )

            user, tokens = auth_service.login(login_data)
            user_data = auth_service._prepare_user_data(user)

            response = make_response(
                jsonify(
                    {
                        "message": "Login successful",
                        "user": user_data,
                        "token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"],
                    }
                ),
                200,
            )

            # Set cookies for both tokens
            response.set_cookie("token", tokens["access_token"], httponly=True)
            response.set_cookie("refresh_token", tokens["refresh_token"], httponly=True)
            return response

        except LoginError as e:
            return jsonify({"error": str(e)}), 401
        except Exception as e:
            logger.error(f"Error logging in user: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @auth_bp.route("/test-verify-user/<username>", methods=["POST", "OPTIONS"])
    def test_verify_user(username):
        if request.method == "OPTIONS":
            return handle_cors_options()

        """Test endpoint to verify a user's email status. Only for testing purposes."""
        try:
            user = user_service.get_user_by_username(username)
            if not user:
                return jsonify({"message": "User not found"}), 404

            user_service.generate_verification_token(user)
            return jsonify({"message": "User verified successfully for testing."}), 200
        except Exception as e:
            logger.error(f"Error during user verification: {str(e)}")
            return jsonify({"error": "Internal server error", "details": str(e)}), 500

    @auth_bp.route("/forgot-password", methods=["POST", "OPTIONS"])
    def forgot_password():
        if request.method == "OPTIONS":
            return handle_cors_options()

        data = request.get_json()
        email = data.get("email")
        frontend_base_url = current_app.config["FRONTEND_BASE_URL"]

        if not email:
            return jsonify({"message": "Email is required"}), 400

        try:
            reset_token = auth_service.initiate_password_reset(email, frontend_base_url)
            response = {"message": "Password reset email sent"}
            if current_app.config.get("TESTING") and reset_token:
                response["reset_token"] = reset_token
            return jsonify(response), 200
        except AuthError as e:
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to initiate password reset: {str(e)}")
            return jsonify({"message": "Internal Server Error"}), 500

    @auth_bp.route("/reset-password/<token>", methods=["POST", "OPTIONS"])
    def reset_password(token):
        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            data = request.get_json() or request.form
            new_password = data.get("new_password")

            if not new_password:
                return jsonify({"message": "New password is required"}), 400

            auth_service.reset_password(token, new_password)
            return jsonify({"message": "Password reset successfully"}), 200
        except AuthError as e:
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to reset password: {str(e)}")
            return jsonify({"message": "Internal Server Error"}), 500

    @auth_bp.route("/logout", methods=["POST", "OPTIONS"])
    def logout():
        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            token = get_token(request)
            if token:
                auth_service.logout(token)

            response = jsonify({"message": "Logged out successfully"})
            # Clear all auth-related cookies
            response.set_cookie("token", "", expires=0)
            response.set_cookie("refresh_token", "", expires=0)
            session.clear()
            return response, 200
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return jsonify({"error": "Error during logout"}), 500

    @auth_bp.route("/check-username/<username>", methods=["GET", "OPTIONS"])
    def check_username(username):
        if request.method == "OPTIONS":
            return handle_cors_options()

        try:
            is_valid, message = auth_service.validate_username(username)
            return jsonify(
                {"available": is_valid, "message": message}
            ), 200 if is_valid else 400
        except Exception as e:
            logger.error(f"Error checking username: {str(e)}")
            return jsonify({"error": "Error checking username"}), 500

    return auth_bp
