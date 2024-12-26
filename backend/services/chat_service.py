from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Dict, Any
from pytz import timezone as pytz_timezone

from flask import jsonify
from loguru import logger
from models.chat import Chat, Message, CitedSection
from models.user import User
from utils.error_handlers import log_error
from services.guest_services import GuestSessionManager


class ChatService:
    """
    The ChatService connects the API endpoints in routes/chat_routes.py with
    the rest of the app. It can create new chats, create a new query within
    a chat, retrieve past chats, and return information back to the API
    endpoint to be sent to the frontend.
    """

    def __init__(self, chat_pdf):
        """
        Initialize the ChatService with necessary dependencies.

        Args:
            chat_pdf: An instance of the ChatPDF class used for processing queries.
        """
        self.chat_pdf = chat_pdf
        self.guest_manager = GuestSessionManager()

    def create_chat(
        self,
        user_id: Optional[str] = None,  # Made optional for guest chats
        time_zone: str = "UTC",
        is_guest: bool = False,
        preset_documents: Optional[Dict[str, Any]] = None,
    ):
        """
                [Previous documentation remains exactly the same until the Args section]

        Args:
            user_id (Optional[str]): The unique identifier of the user creating the chat. Originates
                from MongoDB. For regular users, this is required. For guest chats, this is generated.
            time_zone (str): The user's time zone for accurate timestamping (default is 'UTC').
            is_guest (bool): Flag indicating if this is a guest user chat (default is False).
            preset_documents (Optional[Dict[str, Any]]): Configuration for document filtering:
                {
                    "titles": list[str],  # List of document titles to filter by
                    "index_names": list[str]  # Indices to search in
                }

        Returns:
            tuple: A tuple containing:
                - A JSON response with the new chat's ID, title, and guest status.
                - An HTTP status code (201 Created).

        Example:
            Regular user:
            >>> response, status_code = self.create_chat("66f67ada7f6f4f7f5426a49b",
                                                    time_zone="America/Chicago")
            >>> print(response)
            {"chat_id": "5f3e9b7c8d9e7f1a2b3c4d5e",
            "title": "Aug 19, 2024",
            "is_guest": false}
            >>> print(status_code)
            201

            Guest user with document filter:
            >>> response, status_code = self.create_chat(
            ...     time_zone="UTC",
            ...     is_guest=True,
            ...     preset_documents={
            ...         "titles": ["Document A", "Document B"],
            ...         "index_names": ["index1"]
            ...     }
            ... )
            >>> print(response)
            {"chat_id": "5f3e9b7c8d9e7f1a2b3c4d5e",
            "title": "Chat about: Document A, Document B",
            "is_guest": true,
            "expires_at": "2024-08-20T15:30:00Z",
            "message_limit": 50,
            "messages_remaining": 50,
            "guest_session_id": "guest_abc123",
            "preset_documents": {
                "titles": ["Document A", "Document B"],
                "index_names": ["index1"]
            }}
            >>> print(status_code)
            201

        Note:
            For guest chats, the response includes additional fields:
            - expires_at: When the guest chat will expire
            - message_limit: Maximum number of messages allowed
            - messages_remaining: Number of messages left in the session
            - guest_session_id: Unique identifier for the guest session

            When preset_documents is used:
            - The chat title is automatically generated to reflect the documents
            - All searches within the chat will be limited to the specified documents
            - The original document titles are preserved for reference

            Guest sessions:
            - A new guest user is created automatically for guest chats
            - The guest_session_id is used to authenticate subsequent requests
            - All users accessing the chat via the same link share the session
            - Message limits and expiration are shared across all users of the session
        """
        # Handle guest user creation if needed
        if is_guest:
            user_session = str(user_id).strip()
            if not user_session.startswith("guest_"):
                user_session = f"guest_{user_session}"

            logger.info(f"Using existing guest session: {user_session}")
            guest_user, session_id = self.guest_manager.get_or_create_guest_session(
                user_session
            )
            user = guest_user
            logger.info(f"Retrieved/created guest session: {session_id}")
        else:
            if not user_id:
                logger.error("User ID is required for non-guest chats.")
                return jsonify({"error": "User ID is required"}), 400

            user = User.objects(id=user_id).first()
            if not user:
                logger.error(f"User with ID {user_id} not found.")
                return jsonify({"error": "User not found"}), 404

        user_timezone = pytz_timezone(time_zone)
        current_time = datetime.now(dt_timezone.utc).astimezone(user_timezone)
        title = current_time.strftime("%b %d, %Y")

        params = {
            "user": user,
            "title": title,
            "created_at": current_time,
            "messages": [],
            "is_guest_chat": is_guest,
        }

        if preset_documents and preset_documents.get("titles"):
            params["preset_documents"] = preset_documents
            titles = preset_documents["titles"]

            if len(titles) == 1:
                params["title"] = f"Chat about: {titles[0]}"
            else:
                titles_str = ", ".join(titles[:2])
                if len(titles) > 2:
                    titles_str += f" and {len(titles) - 2} more"
                params["title"] = f"Chat about: {titles_str}"

        if is_guest:
            params.update(
                {
                    "expires_at": current_time + timedelta(hours=6),
                    "message_limit": 50,
                    "current_message_count": 0,
                    "guest_session_id": session_id,
                }
            )

        try:
            new_chat = Chat(**params)
            new_chat.save()
            logger.info(
                f"{'Guest ' if is_guest else ''}Chat created successfully with ID: {new_chat.id}"
            )

            response_data = {
                "chat_id": str(new_chat.id),
                "title": new_chat.title,
                "is_guest": is_guest,
            }

            if is_guest:
                response_data.update(
                    {
                        "expires_at": new_chat.expires_at.isoformat(),
                        "message_limit": new_chat.message_limit,
                        "messages_remaining": new_chat.message_limit,
                        "guest_session_id": session_id,
                    }
                )

            if preset_documents:
                response_data["preset_documents"] = preset_documents

            return jsonify(response_data), 201

        except Exception as e:
            error_message, _ = log_error(e, "Failed to create chat")
            return jsonify({"error": error_message}), 500

    def create_cited_sections(self, citations):
        """
        Create CitedSection objects from citation data.
        """
        cited_sections = []
        for citation in citations:
            cited_section = CitedSection(
                preview=citation.get("preview", ""),
                title=citation.get("title", ""),
                document_id=citation.get("document_id", ""),
                pages=citation.get("pages", []),
                extra_data=citation.get("extra_data", {}),
                index_names=citation.get("index_names", []),
                filter_dimensions=citation.get("filter_dimensions", {}),
                section_title=citation.get("section_title", ""),
                file_url=citation.get("file_url", ""),
                text=citation.get("text", ""),
                index_display_name=citation.get("index_display_name"),
                nominal_creator_name=citation.get("nominal_creator_name"),
                highlighted_file_url=citation.get("highlighted_file_url", ""),
            )
            cited_sections.append(cited_section)
        return cited_sections

    def ask_question_stream(
        self,
        user_id: str,
        query: str,
        chat_id: str,
        index_names: Optional[list[str]] = None,
        filter_dimensions: Optional[dict] = None,
    ):
        """
        Stream response to a user's question with enhanced handling for preset document filters.

        This method processes questions and generates streaming responses while managing:
        - Message creation and storage in MongoDB
        - User authorization and access control
        - Guest session validation
        - Document filtering based on preset configurations
        - User message quotas and limits

        Args:
            user_id (str): The user's ID. Can be either a regular user ID or guest session ID.
            query (str): The user's question or prompt.
            chat_id (str): The chat session identifier.
            index_names (list[str], optional): List of index names to search in.
                Note: Will be overridden by preset document filters if they exist.
            filter_dimensions (dict, optional): Additional filtering criteria.
                Note: Document filtering from preset_documents takes precedence.

        Yields:
            dict: Response chunks in one of these formats:
                - Content: {"type": "content", "text": str}
                - Citations: {"type": "citations", "data": dict}
                - Error: {"type": "error", "message": str, "status": int}

        Authentication:
            - Regular users: Validated against chat.user.id
            - Guest users: Validated against chat.guest_session_id

        Document Filtering:
            If chat.preset_documents exists, it will:
            1. Override provided index_names with preset ones
            2. Apply document title filtering
            3. Maintain conversation focus on specified documents

        Error Handling:
            - 400: Missing required parameters
            - 402: Message quota exceeded
            - 403: Unauthorized access
            - 404: Chat not found
            - 500: Internal processing errors
        """
        logger.debug(
            f"ask_question_stream called with: user_id={user_id}, query='{query}', chat_id={chat_id}"
        )
        logger.debug(
            f"Initial indices={index_names}, filter_dimensions={filter_dimensions}"
        )

        if not query or not chat_id:
            logger.error("Query and chat_id are required.")
            yield {
                "type": "error",
                "message": "Query and chat_id are required.",
                "status": 400,
            }
            return

        chat = Chat.objects(id=chat_id).first()
        logger.debug(f"Fetched chat: {chat}")

        if not chat:
            logger.error(f"Chat with id={chat_id} not found.")
            yield {"type": "error", "message": "Chat not found.", "status": 404}
            return

        # For guest chats, validate using guest_session_id with consistent formatting
        if chat.is_guest_chat:
            # Log the original values
            logger.debug(f"Original user_id: {user_id}, type: {type(user_id)}")
            logger.debug(
                f"Original chat.guest_session_id: {chat.guest_session_id}, type: {type(chat.guest_session_id)}"
            )

            # Get the session IDs, ensuring they're strings
            chat_session = str(chat.guest_session_id).strip()
            user_session = str(user_id).strip()

            # Add guest_ prefix only if needed
            if not chat_session.startswith("guest_"):
                chat_session = f"guest_{chat_session}"
            if not user_session.startswith("guest_"):
                user_session = f"guest_{user_session}"

            logger.debug(
                f"Normalized sessions - Chat: {chat_session}, User: {user_session}"
            )

            # Do case-insensitive comparison
            if chat_session.lower() != user_session.lower():
                logger.error(
                    f"Session mismatch - Chat session: {chat_session}, User session: {user_session}"
                )
                yield {
                    "type": "error",
                    "message": "Access denied. Invalid guest session.",
                    "status": 403,
                }
                return

            # Get user object for guest session
            user = User.objects(session_id=user_session).first()
            if not user:
                # Try without guest_ prefix
                user = User.objects(
                    session_id=user_session.replace("guest_", "", 1)
                ).first()

            if not user:
                logger.error(f"User not found for guest session: {user_session}")
                yield {
                    "type": "error",
                    "message": "User not found for guest session.",
                    "status": 404,
                }
                return

            # Get user object for guest session
            user = User.objects(session_id=user_session).first()
            if not user:
                logger.error(f"User not found for guest session: {user_session}")
                yield {
                    "type": "error",
                    "message": "User not found for guest session.",
                    "status": 404,
                }
                return

            # Check if guest session has expired
            if user.session_expires_at:
                expires_at = user.session_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=dt_timezone.utc)
                if expires_at < datetime.now(dt_timezone.utc):
                    yield {
                        "type": "error",
                        "message": "Guest session has expired. Please generate a new QR code to continue.",
                        "status": 403,
                    }
                    return
        else:
            # For regular chats, validate using user ID
            if str(chat.user.id) != str(user_id):
                logger.error(f"Access denied for user {user_id} to chat {chat_id}")
                yield {
                    "type": "error",
                    "message": "Access denied. User does not own chat.",
                    "status": 403,
                }
                return
            user = chat.user

        try:
            if user.has_reached_message_limit():
                logger.error("User is out of messages.")
                yield {
                    "type": "error",
                    "message": "Message limit reached. Please generate a new QR code to continue.",
                    "status": 402,
                }
                return

            # Check for preset document filters
            document_titles = None
            if hasattr(chat, "preset_documents") and chat.preset_documents:
                document_titles = chat.preset_documents.get("titles")
                index_names = chat.preset_documents.get("index_names")
                logger.info(
                    f"Overriding with preset document filters: {document_titles}"
                )
                logger.info(f"Overriding with preset indices: {index_names}")

            logger.debug(
                f"Final query parameters: document_titles={document_titles}, "
                f"index_names={index_names}, filter_dimensions={filter_dimensions}"
            )

            # Format conversation history
            conversation_history = []
            if chat.messages:
                for msg in chat.messages:  # Use last 5 messages for context
                    conversation_history.append(
                        {
                            "role": "user" if msg.sender == "user" else "assistant",
                            "content": msg.content,
                        }
                    )

            chunks_received = False
            for chunk in self.chat_pdf.stream_process_query(
                query,
                chat_id,
                index_names=index_names,
                filter_dimensions=filter_dimensions,
                document_titles=document_titles,
                conversation_history=conversation_history,
            ):
                logger.debug(f"Processing chunk: {chunk}")
                chunks_received = True

                if isinstance(chunk, tuple):
                    logger.error(f"Unexpected tuple chunk: {chunk}")
                    yield {
                        "type": "error",
                        "message": "Internal error in processing query.",
                    }
                    return

                if chunk.get("type") == "error":
                    logger.debug(f"Yielding error chunk: {chunk}")
                    yield chunk

                elif chunk.get("type") == "content":
                    logger.debug(f"Yielding content chunk: {chunk}")
                    yield chunk

                elif chunk.get("type") == "citations":
                    logger.debug(f"Yielding citations chunk: {chunk}")
                    yield chunk

                    try:
                        # Save messages
                        user_message = Message(sender="user", content=query)
                        chat.messages.append(user_message)

                        # Only generate title for first message if not a filtered chat
                        if len(chat.messages) == 1 and not document_titles:
                            new_title = self.chat_pdf.generate_chat_title(query)
                            if new_title:
                                chat.title = new_title
                                logger.info(f"Generated new title: {new_title}")

                        cited_sections = self.create_cited_sections(
                            chunk.get("cited_sections", [])
                        )

                        ai_response_message = Message(
                            sender="ai",
                            content=chunk.get("full_text"),
                            cited_sections=cited_sections,
                        )
                        chat.messages.append(ai_response_message)

                        # Increment message count after successful processing
                        user.increment_message_count()
                        user.save()

                        chat.save()
                        logger.info(f"Chat {chat_id} updated with new messages")

                    except Exception as e:
                        error_message, _ = log_error(e, "Failed to save chat messages")
                        yield {"type": "error", "message": error_message}

            if not chunks_received:
                logger.warning("No chunks received from stream_process_query")

        except Exception as e:
            error_message, _ = log_error(e, "Error during ask_question_stream")
            yield {"type": "error", "message": error_message}

    def transfer_chat_ownership(
        self, chat_id: str, new_user_id: str
    ) -> tuple[Dict, int]:
        """
        Transfer ownership of a chat from guest to authenticated user.

        Args:
            chat_id: The ID of the chat to transfer
            new_user_id: The ID of the authenticated user taking ownership

        Returns:
            Tuple containing (response_data, status_code)
        """
        try:
            chat = Chat.objects(id=chat_id).first()
            if not chat:
                return {"error": "Chat not found"}, 404

            # Only allow transfer of guest chats
            if not chat.is_guest_chat:
                return {"error": "Cannot transfer non-guest chat"}, 400

            # Update chat ownership
            chat.user = User.objects(id=new_user_id).first()
            chat.is_guest_chat = False
            chat.guest_session_id = None
            chat.expires_at = None
            chat.message_limit = None
            chat.save()

            return {"message": "Chat ownership transferred successfully"}, 200

        except Exception as e:
            logger.error(f"Failed to transfer chat ownership: {str(e)}", exc_info=True)
            return {"error": str(e)}, 500

    def get_chat_history(self, user_id: str, chat_id: str):
        """
        Retrieve the chat history for a specific chat with enhanced guest session handling.

        This method fetches the entire conversation history for a given chat,
        including all messages exchanged between the user and the AI. It ensures
        that only authorized users can access the chat history by implementing:
        - Regular user validation through user ID matching
        - Guest session validation through session ID matching, with support for
        both prefixed ('guest_*') and unprefixed session IDs

        Args:
            user_id (str | ObjectId): The ID of the user requesting the chat history. Can be either:
                - A regular user ID from MongoDB (as string or ObjectId)
                - A guest session ID (with or without 'guest_' prefix)
            chat_id (str): The ID of the chat whose history is being requested.

        Returns:
            tuple: A tuple containing:
                - A JSON response with the chat history (list of messages) or error message
                - An HTTP status code:
                    * 200: Success
                    * 403: Access denied (invalid user/session)
                    * 404: Chat not found
                    * 500: Internal server error

        The returned chat history is a list of message dictionaries, where each message
        contains:
            - sender: The message sender ('user' or 'ai')
            - content: The message content
            - timestamp: ISO formatted timestamp
            - cited_sections: List of citations (if any)

        Example:
            >>> response, status = chat_service.get_chat_history(
            ...     user_id="guest_abc123",
            ...     chat_id="5f3e9b7c8d9e7f1a2b3c4d5e"
            ... )
            >>> if status == 200:
            ...     messages = response.json
            ...     for msg in messages:
            ...         print(f"{msg['sender']}: {msg['content']}")

        Note:
            - For guest sessions, the method handles both prefixed ('guest_abc123')
            and unprefixed ('abc123') session IDs, automatically normalizing them
            for comparison.
            - The user_id parameter can be either a string or ObjectId. It will be
            converted to string format internally for comparison.
        """
        try:
            logger.debug(
                f"get_chat_history called with user_id: {user_id}, chat_id: {chat_id}"
            )

            chat = Chat.objects(id=chat_id).first()
            if not chat:
                logger.error(f"Chat not found: {chat_id}")
                return jsonify({"error": "Chat not found."}), 404

            logger.debug(
                f"Found chat - is_guest_chat: {chat.is_guest_chat}, guest_session_id: {chat.guest_session_id if chat.is_guest_chat else None}"
            )

            # For guest chats, compare session IDs
            if chat.is_guest_chat:
                # Ensure user_id is a string and properly formatted
                user_session = str(user_id).strip()
                if not user_session.startswith("guest_"):
                    user_session = f"guest_{user_session}"

                # Update the chat's session ID to match the current token
                chat.guest_session_id = user_session
                chat.save()
                logger.info(
                    f"Updated chat session ID to match current token: {user_session}"
                )

                # Log the original values
                logger.debug(f"Original user_id: {user_id}, type: {type(user_id)}")
                logger.debug(
                    f"Original chat.guest_session_id: {chat.guest_session_id}, type: {type(chat.guest_session_id)}"
                )

                # Get the session IDs, ensuring they're strings
                chat_session = str(chat.guest_session_id).strip()
                if not chat_session.startswith("guest_"):
                    chat_session = f"guest_{chat_session}"

                logger.debug(
                    f"Normalized sessions - Chat: {chat_session}, User: {user_session}"
                )

                # Do case-insensitive comparison
                if chat_session.lower() != user_session.lower():
                    logger.error(
                        f"Session mismatch - Expected: {chat.guest_session_id}, Got: {user_id}"
                    )
                    return jsonify(
                        {"error": "Access denied. Invalid guest session."}
                    ), 403
            else:
                # For regular chats, compare user IDs
                if str(chat.user.id) != str(user_id):
                    logger.error(
                        f"User ID mismatch - Expected: {chat.user.id}, Got: {user_id}"
                    )
                    return jsonify({"error": "Access denied."}), 403

            # Prepare the chat history
            history = []
            if chat.messages:
                for message in chat.messages:
                    history.append(self._get_message_dictionary(message))
                logger.debug(f"Retrieved {len(history)} messages from chat")
            else:
                logger.warning(f"Chat {chat_id} has no messages.")

            logger.debug(f"Successfully retrieved chat history for chat {chat_id}")
            return jsonify(history), 200

        except Exception as e:
            error_message, _ = log_error(
                e, f"Error retrieving chat history for chat {chat_id}"
            )
            return jsonify({"error": error_message}), 500

    def get_chat_sessions(self, user_id: str):
        """

        This method fetches a list of all chat sessions associated with a given user.
        It provides a summary of each chat, including its ID, title, and creation date.

        Args:
            user_id (str): The ID of the user whose chat sessions are being retrieved.

        Returns:
            tuple: A tuple containing:
                - A JSON response with the list of chat sessions.
                - An HTTP status code (200 OK or 404 Not Found).

        Note:
            The chat sessions are ordered by creation date, with the most recent first.
            This method is useful for populating a user's chat history or allowing them
            to select a previous conversation to continue.
        """
        try:
            # Convert ObjectId to string if needed
            user_id_str = str(user_id)

            # Check if this is a guest session ID
            if user_id_str.startswith("guest_"):
                # For guest users, find chats by guest_session_id
                chats = Chat.objects(guest_session_id=user_id_str).order_by(
                    "-created_at"
                )
            else:
                # For regular users, find chats by user ID
                user = User.objects(id=user_id).first()
                if not user:
                    return jsonify({"error": "User not found."}), 404
                chats = Chat.objects(user=user).order_by("-created_at")

            sessions = []
            for chat in chats:
                sessions.append(
                    {
                        "id": str(chat.id),
                        "title": chat.title,
                        "createdAt": chat.created_at.isoformat(),
                    }
                )

            return jsonify(sessions), 200
        except Exception as e:
            error_message, _ = log_error(e, "Error retrieving chat sessions")
            return jsonify({"error": error_message}), 500

    def get_chat(self, user_id: str, chat_id: str):
        """
        Retrieve a specific chat with relaxed guest session validation.
        This method fetches a chat by its ID and ensures basic access control:
        - For guest chats, allows access regardless of session ID
        - For regular chats, validates using the user ID
        - Handles cases where user_id could be either a session ID or ObjectId
        - Transfers ownership from guest chat to user chat

        Args:
            user_id (str): Either a guest session ID ('guest_*') or user ObjectId
            chat_id (str): The ID of the chat to retrieve

        Returns:
            tuple: (response, status_code) where:
                - response: JSON with chat data or error message
                - status_code: HTTP status code (200, 403, 404, 500)
        """
        try:
            chat = Chat.objects(id=chat_id).first()
            if not chat:
                return {"error": "Chat not found"}, 404

            # Handle potential ownership transfer for guest chats
            if chat.is_guest_chat and not str(user_id).startswith("guest_"):
                # Transfer ownership if an authenticated user accesses a guest chat
                transfer_result, status = self.transfer_chat_ownership(chat_id, user_id)
                if status != 200:
                    return transfer_result, status

                # Refresh chat object after transfer
                chat.reload()

            # Regular access control
            if not chat.is_guest_chat and str(chat.user.id) != str(user_id):
                return {"error": "Access denied"}, 403

            chat_data = {
                "id": str(chat.id),
                "title": chat.title,
                "createdAt": chat.created_at,
                "messages": [
                    self._get_message_dictionary(message) for message in chat.messages
                ],
                "preset_documents": chat.preset_documents,
            }

            return jsonify(chat_data), 200

        except Exception as e:
            logger.error(f"Error retrieving chat {chat_id}: {str(e)}", exc_info=True)
            return {"error": str(e)}, 500

    def _get_message_dictionary(self, message):
        logger.info(f"Mongoized message format: {message.to_mongo()}")
        return {
            "sender": message.sender,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "cited_sections": (
                [
                    {
                        "preview": cs.preview,
                        "title": cs.title,
                        "document_id": cs.document_id,
                        "pages": cs.pages,
                        "extra_data": cs.extra_data,
                        "index_names": cs.index_names,
                        "filter_dimensions": cs.filter_dimensions,
                        "section_title": cs.section_title,
                        "file_url": cs.file_url,
                        "highlighted_file_url": cs.highlighted_file_url,
                        "index_display_name": cs.index_display_name,
                        "nominal_creator_name": cs.nominal_creator_name,
                    }
                    for cs in message.cited_sections
                ]
                if message.cited_sections
                else []
            ),
        }
