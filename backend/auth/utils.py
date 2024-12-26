from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app, make_response, Response
import jwt
from mongoengine import DoesNotExist
from models.user import User
from loguru import logger
from utils.error_handlers import log_error, create_error_response
from werkzeug.exceptions import Forbidden
from services.guest_services import GuestSessionManager

# Define endpoints that require full authentication (no guest access)
GUEST_RESTRICTED_ENDPOINTS = {
    "filter.get_visibilities",
    "filter.create_filter_dimension",
    "filter.add_value_to_filter_dimension",
    "filter.filter_documents",
    "documents.upload",
    "documents.delete",
    "organization.create_organization",
    "organization.update_member_role",
    "organization.add_admin",
    "organization.join_request",
    # Add other endpoints that require full auth
}


def decode_token(token, secret_key=None):
    """
    Decode a token, handling both JWT and guest token formats.

    Args:
        token (str): The token to decode.
        secret_key (str, optional): Secret key for JWT decoding. If not provided,
                                  will attempt to get from Flask app config.

    Returns:
        dict: The decoded token payload.

    Raises:
        ValueError: If the token format is invalid.
    """
    try:
        if not token or token == "null":
            raise ValueError("Missing or invalid token")

        if len(token.split(".")) == 3:
            secret = secret_key or current_app.config["SECRET_KEY"]
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
        else:
            if token.startswith("guest_"):
                session_id = token.split("guest_")[1]
                decoded = {
                    "is_guest": True,
                    "session_id": f"guest_{session_id}",
                    "user_id": f"guest_{session_id}",
                }
            else:
                raise ValueError("Invalid token format")
        return decoded
    except Exception as e:
        logger.error(f"Token decode error: {str(e)}, Token: {token}")
        raise ValueError(f"Failed to decode token: {str(e)}")


def get_current_user_id(request):
    """
    Get the current user's ID from the authorization token.

    Returns:
        str: The user ID.

    Raises:
        ValueError: If the token is missing, invalid, or doesn't contain a user ID.
    """
    url_session = request.args.get("session")
    logger.debug(f"URL Session: {url_session}")
    logger.debug(f"Auth Header: {request.headers.get('Authorization')}")
    logger.debug(f"Cookie Token: {request.cookies.get('token')}")
    token = get_token(request)
    if not token:
        raise ValueError("Authorization token is missing")

    decoded_token = decode_token(token)
    if not decoded_token:
        raise ValueError("Invalid token")

    user_id = decoded_token.get("user_id")
    if not user_id:
        raise ValueError("User ID not found in token")

    return user_id


def generate_token(user_data: dict, secret_key=None, expires_in=timedelta(days=1)):
    """
    Generate a JWT token for either a regular user or guest session with customizable expiration.

    Args:
        user_data (dict): The user data for which to generate the token. For guest sessions,
                         only requires id, is_guest, and session_id fields.
        secret_key (str, optional): Secret key for JWT encoding. If not provided,
                                  will attempt to get from Flask app config.
        expires_in (timedelta): The time duration before the token expires
                              (default: 1 day for regular users, 24 hours for guests).

    Returns:
        str: The encoded JWT token.

    Note:
        Guest tokens contain minimal payload while regular user tokens include full user details.
        This maintains efficiency for guest sessions while preserving functionality for regular users.
    """
    if user_data.get("is_guest"):
        # For guest users, return the session_id directly (it already has the guest_ prefix)
        return user_data["session_id"]

    payload = {
        "id": user_data["id"],
        "user_id": user_data["id"],
        "is_guest": False,
        "exp": datetime.now(timezone.utc) + expires_in,
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "username": user_data["username"],
        "email": user_data["email"],
        "personal_index_name": user_data["personal_index_name"],
        "is_superadmin": user_data["is_superadmin"],
        "subscription_status": user_data["subscription_status"],
        "cycle_token_limit": user_data["cycle_token_limit"],
    }

    secret = secret_key or current_app.config["SECRET_KEY"]
    return jwt.encode(payload, secret, algorithm="HS256")


def get_token(request):
    """
    Retrieve the token from the request, prioritizing URL sessions over cookies and headers.

    Args:
        request (Request): The Flask request object.

    Returns:
        str: The token if found, or None if not present.
    """

    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split()[1]

    # Check cookies
    token = request.cookies.get("token")
    if token and token != "null":
        return token

    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if endpoint requires full authentication
        if request.endpoint in GUEST_RESTRICTED_ENDPOINTS:
            token = get_token(request)
            if not token:
                return jsonify({"error": "Authentication required"}), 401

            try:
                token_data = decode_token(token)
                if token_data.get("is_guest", False):
                    return jsonify(
                        {"error": "This endpoint requires full authentication"}
                    ), 401

                user = User.objects.get(id=token_data.get("user_id"))
                if token in user.blacklisted_tokens:
                    return jsonify({"error": "Token is blacklisted"}), 401

                try:
                    return f(user, *args, **kwargs)
                except Forbidden as e:
                    logger.error(f"Authorization error: {str(e)}")
                    return jsonify({"error": str(e)}), 403
                except Exception as e:
                    logger.error(f"Token validation error: {str(e)}")
                    return jsonify({"error": str(e)}), 401

            except (
                jwt.ExpiredSignatureError,
                jwt.InvalidTokenError,
                DoesNotExist,
            ) as e:
                logger.error(f"Token validation error: {str(e)}")
                return jsonify({"error": "Invalid or expired token"}), 401
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return jsonify({"error": "Authentication failed"}), 401

        # Handle guest and regular authentication
        guest_manager = GuestSessionManager()
        url_session = request.args.get("session")
        logger.debug(f"URL session parameter: {url_session}")

        # Handle token-based authentication
        token = get_token(request)
        if token:
            try:
                token_data = decode_token(token)
                user_id = token_data.get("user_id")
                is_guest = token_data.get("is_guest", False)
                session_id = token_data.get("session_id")

                logger.info(
                    f"Decoded token - user_id: {user_id}, is_guest: {is_guest}, session_id: {session_id}"
                )

                if is_guest:
                    guest_user = User.objects(session_id=session_id).first()
                    if guest_user and guest_manager.is_session_valid(guest_user):
                        try:
                            return f(guest_user, *args, **kwargs)
                        except Forbidden as e:
                            logger.error(f"Authorization error: {str(e)}")
                            return jsonify({"error": str(e)}), 403
                        except Exception as e:
                            logger.error(f"Token validation error: {str(e)}")
                            return jsonify({"error": str(e)}), 401
                    else:
                        # Create new session if the token session is invalid
                        logger.info(
                            f"Token session {session_id} invalid, creating new session"
                        )
                        try:
                            new_guest_user, new_session_id = (
                                guest_manager.create_guest_session()
                            )
                            logger.info(f"Created new guest session: {new_session_id}")

                            new_token = generate_token(
                                {
                                    "id": new_session_id,
                                    "user_id": new_session_id,
                                    "is_guest": True,
                                    "session_id": new_session_id,
                                },
                                expires_in=timedelta(hours=24),
                            )

                            response = f(new_guest_user, *args, **kwargs)
                            if isinstance(response, tuple):
                                response_data, status_code = response
                                response = make_response(response_data, status_code)
                            elif not isinstance(response, Response):
                                response = make_response(response)

                            response.set_cookie("token", new_token, httponly=True)
                            return response
                        except Exception as e:
                            logger.error(
                                f"Failed to create new guest session: {str(e)}"
                            )
                            return jsonify(
                                {"error": "Failed to create new guest session"}
                            ), 500
                else:
                    user = User.objects.get(id=user_id)
                    if token in user.blacklisted_tokens:
                        return jsonify({"error": "Token is blacklisted"}), 401
                    try:
                        return f(user, *args, **kwargs)
                    except Forbidden as e:
                        logger.error(f"Authorization error: {str(e)}")
                        return jsonify({"error": str(e)}), 403
                    except Exception as e:
                        logger.error(f"Token validation error: {str(e)}")
                        return jsonify({"error": str(e)}), 401

            except (
                jwt.ExpiredSignatureError,
                jwt.InvalidTokenError,
                DoesNotExist,
            ) as e:
                logger.error(f"Token validation error: {str(e)}")
                return jsonify({"error": "Invalid or expired token"}), 401
            except Exception as e:
                log_error(e, "Token validation error")
                return jsonify({"error": "Invalid or expired token"}), 401

        # Create new guest session if no token exists
        try:
            guest_user, session_id = guest_manager.get_or_create_guest_session()
            session_id = (
                session_id if session_id.startswith("guest_") else f"guest_{session_id}"
            )
            logger.debug(f"Created new guest session: {session_id}")

            token = generate_token(
                {
                    "id": session_id,
                    "user_id": session_id,
                    "is_guest": True,
                    "session_id": session_id,
                },
                expires_in=timedelta(hours=24),
            )

            try:
                response = f(guest_user, *args, **kwargs)
                if isinstance(response, tuple):
                    response_data, status_code = response
                    response = make_response(response_data, status_code)
                elif not isinstance(response, Response):
                    response = make_response(response)

                response.set_cookie("token", token, httponly=True)
                return response
            except Forbidden as e:
                logger.error(f"Authorization error: {str(e)}")
                return jsonify({"error": str(e)}), 403
            except Exception as e:
                logger.error(f"Token validation error: {str(e)}")
                return jsonify({"error": str(e)}), 401

        except Exception as e:
            error_message, stack_trace = log_error(e, "Failed to create guest session")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    return decorated


def check_user_role(user, organization_id, required_role):
    """
    Check if a user has the required role in a specific organization.

    Note: Direct DB query for role check - keeps auth middleware simple and fast.
    Complex role logic should be handled by service layer post-authentication.

    Args:
        user (User): The user object.
        organization_id (str): The ID of the organization.
        required_role (str): The required role ('member', 'editor', or 'admin').

    Returns:
        bool: True if the user has the required role or higher, False otherwise.
    """
    from models.user_organization import UserOrganization

    membership = UserOrganization.objects(
        user=user.id, organization=organization_id
    ).first()
    if not membership:
        return False

    role_hierarchy = ["member", "editor", "admin"]
    return role_hierarchy.index(membership.role) >= role_hierarchy.index(required_role)


def role_required(required_role):
    """
    Decorator for routes requiring specific organization role.

    Note: Keeps direct DB access for auth middleware efficiency.
    Complex role logic should be handled by service layer post-authentication.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(user, *args, **kwargs):
            organization_id = kwargs.get("organization_id") or request.json.get(
                "organization_id"
            )
            if not organization_id:
                error_message, stack_trace = log_error(
                    ValueError("Organization ID is required"), "Role validation error"
                )
                return jsonify(create_error_response(error_message, stack_trace)), 400

            if not check_user_role(user, organization_id, required_role):
                error_message, stack_trace = log_error(
                    ValueError(f"User does not have the required {required_role} role"),
                    "Role validation error",
                )
                return jsonify(create_error_response(error_message, stack_trace)), 403

            return f(user, *args, **kwargs)

        return decorated_function

    return decorator


def superadmin_required(f):
    """
    Decorator for routes requiring superadmin access.

    Note: Simple boolean check, no need for service layer.
    """

    @wraps(f)
    def decorated_function(user, *args, **kwargs):
        if not user.is_superadmin:
            error_message, stack_trace = log_error(
                ValueError("Superadmin access required"), "Authorization error"
            )
            return jsonify(create_error_response(error_message, stack_trace)), 403
        return f(user, *args, **kwargs)

    return decorated_function


def validate_input(required_fields):
    """Decorator for validating required request fields."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                error_message, stack_trace = log_error(
                    ValueError(f"Missing required fields: {', '.join(missing_fields)}"),
                    "Input validation error",
                )
                return jsonify(create_error_response(error_message, stack_trace)), 400
            return f(*args, **kwargs)

        return decorated_function

    return decorator
