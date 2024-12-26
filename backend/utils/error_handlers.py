import traceback
from typing import Optional, Tuple
from flask import jsonify
from loguru import logger
from functools import wraps
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound


def log_error(error: Exception, context: str) -> Tuple[str, str]:
    """
    Internal utility for consistent error logging across services.
    Returns the error message and stack trace for debugging purposes.

    Args:
        error: The exception that occurred
        context: Description of where/why the error occurred

    Returns:
        Tuple of (error_message, stack_trace)
    """
    error_message = f"{context}: {str(error)}"
    stack_trace = traceback.format_exc()
    logger.exception(f"{error_message}\n{stack_trace}")
    return error_message, stack_trace


def create_error_response(
    error_message: str, stack_trace: Optional[str] = None
) -> dict:
    """
    Creates a standardized error response structure.
    Framework-agnostic - does not handle response formatting.

    Args:
        error_message: The error message to return to the client
        stack_trace: Optional stack trace (only included in development/debug)

    Returns:
        Dictionary containing the error response structure
    """
    response = {"message": error_message}
    if stack_trace:
        response["stack_trace"] = stack_trace
    return response


def handle_errors(f):
    """
    Decorator for Flask routes to handle errors consistently.
    Converts exceptions to appropriate HTTP responses.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BadRequest as e:
            error_message, stack_trace = log_error(e, "Bad request")
            return jsonify(create_error_response(error_message, stack_trace)), 400
        except Unauthorized as e:
            error_message, stack_trace = log_error(e, "Unauthorized access")
            return jsonify(create_error_response(error_message, stack_trace)), 401
        except Forbidden as e:
            error_message, stack_trace = log_error(e, "Forbidden access")
            return jsonify(create_error_response(error_message, stack_trace)), 403
        except NotFound as e:
            error_message, stack_trace = log_error(e, "Resource not found")
            return jsonify(create_error_response(error_message, stack_trace)), 404
        except Exception as e:
            error_message, stack_trace = log_error(e, "An unexpected error occurred")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    return decorated_function
