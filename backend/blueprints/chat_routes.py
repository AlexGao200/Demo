from utils.error_handlers import handle_errors
from loguru import logger
import json
from auth.utils import token_required
from services.qr_code_service import QRCodeService
from models.chat import Chat

from flask import (
    Blueprint,
    Response,
    jsonify,
    request,
    stream_with_context,
)


def generate_stream(
    chat_service, user_identifier, query, chat_id, indices, filter_dimensions
):
    """Helper function to generate the stream of events."""
    try:
        for chunk in chat_service.ask_question_stream(
            user_identifier,
            query,
            chat_id,
            indices,
            filter_dimensions,
        ):
            if isinstance(chunk, dict):
                event_data = json.dumps(chunk)
                yield f"data: {event_data}\n\n"

        # Always send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"Error in generate_stream: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


def create_chat_blueprint(chat_service, limiter, EmailService):
    chat_bp = Blueprint("chat", __name__, url_prefix="/api")

    @chat_bp.route("/chat_history", methods=["GET"])
    @handle_errors
    @token_required
    def get_chat_history(current_user):
        """Retrieve the chat history for a specific chat."""
        chat_id = request.args.get("chat_id")

        # Use session_id for guest users, user_id for regular users
        if getattr(current_user, "is_guest", False):
            user_identifier = current_user.session_id
            logger.debug(f"Using guest session ID for auth: {user_identifier}")
        else:
            user_identifier = current_user.id
            logger.debug(f"Using user ID for auth: {user_identifier}")

        result, status_code = chat_service.get_chat_history(
            user_id=user_identifier,  # We keep the parameter name as user_id for backward compatibility
            chat_id=chat_id,
        )
        return result, status_code

    @chat_bp.route("/chat", methods=["POST"])
    @token_required
    @handle_errors
    def create_chat(current_user):
        """
        Create a new chat for either a regular or guest user.

        The route handles both types of users transparently, with the distinction
        being made in the chat service based on the user's properties.

        Args:
            current_user: The authenticated user object (can be regular or guest user)
                        Automatically provided by token_required decorator

        Returns:
            tuple: (response, status_code) where response includes:
                - chat_id: The ID of the created chat
                - title: The chat title
                - is_guest: Boolean indicating if this is a guest chat
                - expires_at: (guest only) When the chat expires
                - messages_remaining: (guest only) Number of messages allowed
        """
        time_zone = request.json.get("time_zone", "UTC")

        # Log the type of user creating the chat
        logger.info(
            f"Creating chat for {'guest' if getattr(current_user, 'is_guest', False) else 'regular'} user: {current_user.id}"
        )

        result, status_code = chat_service.create_chat(
            user_id=current_user.id,
            time_zone=time_zone,
            is_guest=getattr(current_user, "is_guest", False),
        )

        if status_code == 201 and isinstance(result, Response):
            result_data = result.get_json()
            logger.debug(
                f"Chat created - ID: {result_data.get('chat_id')}, "
                f"Guest: {result_data.get('is_guest', False)}"
            )

            # For guest chats, log expiration
            if result_data.get("is_guest"):
                logger.debug(
                    f"Guest chat will expire at: {result_data.get('expires_at')}, "
                    f"Messages remaining: {result_data.get('messages_remaining')}"
                )

        return result, status_code

    @chat_bp.route("/ask_stream", methods=["POST"])
    @limiter.limit("10 per minute")
    @token_required
    def ask_stream(current_user):
        try:
            logger.debug(f"Incoming request payload: {request.json}")
            logger.info(
                f"User Context - ID: {current_user.id}, "
                f"Is Guest: {getattr(current_user, 'is_guest', False)}, "
                f"Session ID: {getattr(current_user, 'session_id', None)}"
            )

            query = request.json.get("query")
            chat_id = request.json.get("chat_id")
            indices = request.json.get("indices")
            filter_dimensions = request.json.get("filter_dimensions")

            chat = Chat.objects(id=chat_id).first()
            if chat:
                logger.info(
                    f"Chat Info - ID: {chat_id}, "
                    f"Is Guest Chat: {chat.is_guest_chat}, "
                    f"Guest Session ID: {chat.guest_session_id if chat.is_guest_chat else None}, "
                    f"User ID: {chat.user.id if not chat.is_guest_chat else None}"
                )

                # Handle guest chat session alignment
                if chat.is_guest_chat and hasattr(current_user, "session_id"):
                    logger.info(
                        f"Session Alignment Check - "
                        f"Chat Guest Session: {chat.guest_session_id}, "
                        f"User Context Session: {current_user.session_id}"
                    )

                    if chat.guest_session_id != current_user.session_id:
                        logger.info("Updating chat user to match current guest session")
                        try:
                            # Update the chat's user and guest_session_id
                            chat.user = current_user
                            chat.guest_session_id = current_user.session_id
                            chat.save()

                            logger.info(
                                f"Successfully updated chat user and session ID: "
                                f"User: {current_user.id}, "
                                f"Session: {current_user.session_id}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to update chat user: {str(e)}")
                            return jsonify(
                                {
                                    "type": "error",
                                    "message": "Failed to update chat session",
                                }
                            ), 500

            user_identifier = (
                current_user.session_id
                if getattr(current_user, "is_guest", False)
                else str(current_user.id)
            )
            logger.info(f"Using user identifier for stream: {user_identifier}")

            def generate():
                try:
                    for chunk in chat_service.ask_question_stream(
                        user_identifier,
                        query,
                        chat_id,
                        indices,
                        filter_dimensions,
                    ):
                        if isinstance(chunk, dict):
                            if chunk.get("type") == "error":
                                logger.error(f"Error chunk received: {chunk}")
                            event_data = json.dumps(chunk)
                            yield f"data: {event_data}\n\n".encode("utf-8")

                    logger.info(f"Stream completed for chat {chat_id}")
                    yield f"data: {json.dumps({'type': 'done'})}\n\n".encode("utf-8")

                except Exception as e:
                    logger.error(f"Error in stream for chat {chat_id}: {str(e)}")
                    error_event = json.dumps({"type": "error", "message": str(e)})
                    yield f"data: {error_event}\n\n".encode("utf-8")

            return Response(
                stream_with_context(generate()),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        except Exception as e:
            logger.error(f"Error in ask_stream endpoint: {str(e)}")
            return jsonify({"type": "error", "message": str(e)}), 500

    @chat_bp.route("/chat_sessions", methods=["GET"])
    @token_required
    @handle_errors
    def get_chat_sessions(current_user):
        """Retrieve all chat sessions for the authenticated user."""
        response, status_code = chat_service.get_chat_sessions(current_user.id)
        return response, status_code

    @chat_bp.route("/chat/<chat_id>", methods=["GET"])
    @token_required
    @handle_errors
    def get_chat(current_user, chat_id):
        """
        Get a specific chat, handling both guest and authenticated access.

        The token_required decorator will provide either:
        - A regular user object for authenticated users
        - A guest user object for guest sessions
        """
        try:
            # Determine the appropriate user ID based on user type
            if getattr(current_user, "is_guest", False):
                user_id = (
                    current_user.session_id
                )  # The decorator already handles guest_ prefix
            else:
                user_id = str(current_user.id)

            logger.info(
                f"Getting chat {chat_id} for user {user_id} (guest: {getattr(current_user, 'is_guest', False)})"
            )

            # Get the chat using the chat service
            result, status_code = chat_service.get_chat(user_id, chat_id)

            if status_code != 200:
                logger.error(
                    f"Failed to get chat {chat_id} for user {user_id}: {result}"
                )
                return result, status_code

            return result, 200

        except Exception as e:
            logger.error(f"Error in get_chat endpoint: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @chat_bp.route("/create_qr_code", methods=["POST"])
    @token_required
    @handle_errors
    def create_qr_code(current_user):
        """Create a QR code that links to a chat with pre-loaded documents."""
        try:
            data = request.get_json()
            qr_service = QRCodeService(chat_service)
            response, status = qr_service.create_qr_chat(
                document_ids=data.get("document_ids", []), creating_user=current_user
            )
            return jsonify(response), status

        except Exception as e:
            logger.error(f"Failed to create QR code: {str(e)}")
            return jsonify({"error": f"Failed to create QR code: {str(e)}"}), 500

    @chat_bp.route("/send_qr_code_email", methods=["POST"])
    @token_required
    @handle_errors
    def send_qr_code_email(
        user,
    ):  # Add user parameter to receive the authenticated user
        """
        Endpoint to send QR code link via email.
        Requires authentication.

        Expected JSON body:
        {
            "email": "recipient@example.com",
            "link": "https://example.com/qr/...",
            "document_title": "Document Title"
        }
        """
        data = request.get_json()

        if not all(key in data for key in ["email", "link", "document_title"]):
            return jsonify(
                {
                    "error": "Missing required fields: email, link, and document_title are required"
                }
            ), 400

        email = data["email"]
        link = data["link"]
        document_title = data["document_title"]

        # Validate email format
        if not isinstance(email, str) or "@" not in email:
            return jsonify({"error": "Invalid email format"}), 400

        try:
            # Send the email
            EmailService.send_qr_code_email(email, link, document_title)

            logger.info(
                f"QR code email sent successfully to {email} by user {user.email}"
            )
            return jsonify(
                {"message": "Email sent successfully", "status": "success"}
            ), 200

        except Exception as e:
            logger.error(f"Error sending QR code email: {str(e)}")
            return jsonify(
                {"error": "Failed to send email", "status": "error", "message": str(e)}
            ), 500

    return chat_bp
