from typing import List, Dict, Tuple
from loguru import logger
from flask import current_app
from models.file_metadata import FileMetadata
from models.user import User


class QRCodeService:
    """
    Service for handling QR code-based chat creation and access.
    Manages document validation, chat creation, and access control for QR-generated chats.
    """

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def create_qr_chat(
        self, document_ids: List[str], creating_user: User
    ) -> Tuple[Dict, int]:
        """
        Create a new chat accessible via QR code.
        Starts as a guest chat but can be converted to user chat when accessed.

        Args:
            document_ids: List of document IDs to include in chat
            creating_user: User creating the QR code (for document access validation)

        Returns:
            Tuple[Dict, int]: Response data and status code
        """
        try:
            # Validate documents and get metadata
            documents = self._validate_documents(document_ids, creating_user)

            # Prepare chat configuration
            chat_config = self._prepare_chat_config(documents)

            # Create initial guest chat
            chat_result, status = self.chat_service.create_chat(
                user_id=None,  # Start as guest chat
                time_zone="UTC",
                is_guest=True,
                preset_documents=chat_config,
            )

            if status != 201:
                raise ValueError("Failed to create chat")

            # Generate response with chat link
            return self._generate_qr_response(chat_result.get_json(), documents)

        except ValueError as e:
            logger.warning(f"Validation error in create_qr_chat: {str(e)}")
            return {"error": str(e)}, 400
        except Exception as e:
            logger.error(f"Error creating QR chat: {str(e)}", exc_info=True)
            return {"error": f"Failed to create QR chat: {str(e)}"}, 500

    def _validate_documents(
        self, document_ids: List[str], user: User
    ) -> List[FileMetadata]:
        """Validate document access and existence."""
        if not document_ids:
            raise ValueError("document_ids is required")

        documents = []
        for doc_id in document_ids:
            document = FileMetadata.objects(id=doc_id).first()
            if not document:
                raise ValueError(f"Document not found: {doc_id}")

            if document.visibility == "private" and str(
                document.originating_user.id
            ) != str(user.id):
                raise ValueError(f"Access denied for document: {doc_id}")

            documents.append(document)
        return documents

    def _prepare_chat_config(self, documents: List[FileMetadata]) -> Dict:
        """Prepare chat configuration with document information."""
        return {
            "titles": [doc.title for doc in documents],
            "index_names": list(set(sum([doc.index_names for doc in documents], []))),
        }

    def _generate_qr_response(
        self, chat_data: Dict, documents: List[FileMetadata]
    ) -> Tuple[Dict, int]:
        """Generate response for QR code creation."""
        chat_id = chat_data.get("chat_id")
        session_id = chat_data.get("guest_session_id")

        frontend_url = current_app.config.get(
            "FRONTEND_BASE_URL", "http://localhost:3000"
        )
        chat_link = f"{frontend_url}/chat/{chat_id}"  # No session in link

        return {
            "chat_id": chat_id,
            "chat_link": chat_link,
            "titles": [doc.title for doc in documents],
            "original_document_ids": [str(doc.id) for doc in documents],
            "expires_at": chat_data.get("expires_at"),
            "guest_session_id": session_id,
        }, 201
