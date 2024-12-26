from flask import (
    Blueprint,
    jsonify,
    request,
    send_from_directory,
)
from auth.utils import token_required
from utils.error_handlers import log_error, create_error_response, handle_errors
from loguru import logger
import os
from models.action_log import ActionLog
from models.chat import Chat
from models.user import User
from models.organization import Organization
from models.file_metadata import FileMetadata
from models.user_organization import UserOrganization
import asyncio
from models.index_registry import IndexRegistry
import json
from services.rag import ChatPDF
from services.file_service import FileService
from flask_limiter import Limiter
from flask import current_app


def create_file_blueprint(
    chat_pdf: ChatPDF, file_service: FileService, limiter: Limiter
):
    file_bp = Blueprint("file", __name__, url_prefix="/api")

    @file_bp.route("/upload", methods=["POST"])
    @token_required
    @handle_errors
    def unified_upload(current_user):
        try:
            logger.info(f"Form Data Received: {request.form}")

            # Extract uploaded files and form data
            uploaded_files = request.files.getlist("files")
            titles = request.form.getlist("titles")
            file_visibilities = json.loads(request.form.get("file_visibilities"))
            nominal_creator_names = request.form.getlist("nominal_creator_name")
            filter_dimensions = json.loads(request.form.get("filter_dimensions", "{}"))
            index_names = request.form.get("index_names").split(
                ","
            )  # FIXME change to getlist

            # Log the received data
            logger.info(f"Filter dimensions received: {filter_dimensions}")
            logger.info(f"Index names received: {index_names}")
            logger.info(f"Creator org display names received: {nominal_creator_names}")

            # Validate input data
            if not index_names:
                error_message, _ = log_error(
                    ValueError("index_names are required"), "Input validation"
                )
                return jsonify(create_error_response(error_message)), 400

            if not file_visibilities:
                error_message, _ = log_error(
                    ValueError("No file visibilities provided"), "Input validation"
                )
                return jsonify(create_error_response(error_message)), 400

            if not uploaded_files:
                error_message, _ = log_error(
                    ValueError("No files provided"), "Input validation"
                )
                return jsonify(create_error_response(error_message)), 400

            if len(uploaded_files) != len(titles):
                error_message, _ = log_error(
                    ValueError("Mismatch between number of files and titles"),
                    "Input validation",
                )
                return jsonify(create_error_response(error_message)), 400

            # Check permissions for each index
            logger.info(file_visibilities)
            if isinstance(file_visibilities, dict):
                file_visibilities = list(file_visibilities.values())
            if len(file_visibilities) == 1:
                file_visibilities = file_visibilities * len(titles)
            logger.info(file_visibilities)

            organizations_to_update = []
            for index_name in index_names:
                if index_name == current_user.personal_index_name:
                    continue  # User always has permission for their personal index

                organization = Organization.objects(index_name=index_name).first()
                if not organization:
                    error_message, _ = log_error(
                        ValueError(f"Organization not found for index: {index_name}"),
                        "Permission check",
                    )
                    return jsonify(create_error_response(error_message)), 404

                user_org = UserOrganization.objects(
                    user=current_user.id, organization=organization.id
                ).first()
                if not user_org or user_org.role not in ["admin", "editor"]:
                    error_message, _ = log_error(
                        ValueError(f"Insufficient permissions for index: {index_name}"),
                        "Permission check",
                    )
                    return jsonify(create_error_response(error_message)), 403

                # Track organizations to update has_public_documents if public files are uploaded
                if "public" in file_visibilities:
                    organizations_to_update.append(organization)

            # Proceed with file processing
            results = []
            for i, uploaded_file in enumerate(uploaded_files):
                logger.info(
                    f"Processing file: {uploaded_file.filename}, Title: {titles[i]}, Index: {index_names[0]}"
                )
                result = asyncio.run(
                    file_service.process_upload(
                        uploaded_file,
                        titles[i],
                        [
                            index_names[0]
                        ],  # Use the first index name for now, consider multiple indices in the future
                        file_visibility=file_visibilities[i],
                        user_id=current_user.id,
                        nominal_creator_name=(
                            nominal_creator_names[i] if nominal_creator_names else None
                        ),
                        filter_dimensions=filter_dimensions,
                    )
                )

                # Handle both success and error cases
                if isinstance(result, dict) and "error" in result:
                    error_message, _ = log_error(
                        ValueError(result["error"]), "File processing"
                    )
                    return jsonify(create_error_response(error_message)), 400

                results.append(result)

            # Log the successful upload
            ActionLog.log_action(
                originating_user=current_user,
                action_type="upload_doc",
                target_documents=[
                    FileMetadata.objects(s3_url=result["s3_url"]).first()
                    for result in results
                    if "s3_url" in result
                ],
                target_indices=[
                    IndexRegistry.objects.get(index_name=index_name)
                    for index_name in index_names
                ],
                description=f"Uploaded {len(results)} document(s) to indices: {', '.join(index_names)}",
            )

            # Update organization public document status if public files were uploaded
            for organization in organizations_to_update:
                organization.update_public_documents_status()

            # Return success response
            return (
                jsonify(
                    {"message": "Files uploaded and processed.", "results": results}
                ),
                200,
            )

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error processing upload")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    @file_bp.route("/upload/<doc_id>/status", methods=["GET"])
    @token_required
    @handle_errors
    def get_upload_status(current_user, doc_id):
        """Get the current status of a document upload and processing."""
        try:
            # Fetch document metadata
            metadata = FileMetadata.objects(id=doc_id).first()
            if not metadata:
                error_message, _ = log_error(
                    ValueError(f"Document not found: {doc_id}"), "Document lookup"
                )
                return jsonify(create_error_response(error_message)), 404

            # Check permissions
            has_permission = False

            # Check if it's user's personal index
            if any(
                index == current_user.personal_index_name
                for index in metadata.index_names
            ):
                has_permission = True

            # Check organization permissions
            if not has_permission:
                for index_name in metadata.index_names:
                    organization = Organization.objects(index_name=index_name).first()
                    if organization:
                        user_org = UserOrganization.objects(
                            user=current_user.id, organization=organization.id
                        ).first()
                        if user_org:
                            has_permission = True
                            break

            if not has_permission:
                error_message, _ = log_error(
                    ValueError("Insufficient permissions to view document status"),
                    "Permission check",
                )
                return jsonify(create_error_response(error_message)), 403

            # Return status information
            return jsonify(
                {
                    "status": metadata.processing_status,
                    "progress": metadata.processing_progress,
                    "step": metadata.processing_step,
                    "error": metadata.processing_error,
                    "started_at": metadata.processing_started_at.isoformat()
                    if metadata.processing_started_at
                    else None,
                    "completed_at": metadata.processing_completed_at.isoformat()
                    if metadata.processing_completed_at
                    else None,
                }
            ), 200

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error retrieving upload status")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    @file_bp.route("/tmp/<path:filename>")
    @token_required
    @handle_errors
    def serve_tmp_file(current_user, filename):
        try:
            logger.debug(f"Received request to serve file: {filename}")

            file_path = os.path.join(current_app.config["TMP_DIR"], filename)
            logger.debug(f"Constructed file path: {file_path}")

            chat_id = request.args.get("chat_id")
            if not chat_id:
                error_message, _ = log_error(
                    ValueError("chat_id is required"), "Parameter validation"
                )
                return jsonify(create_error_response(error_message)), 400

            chat = Chat.objects(id=chat_id).first()
            if not chat:
                error_message, _ = log_error(
                    ValueError(f"Chat with id {chat_id} not found"), "Resource lookup"
                )
                return jsonify(create_error_response(error_message)), 404

            # Log chat data to ensure it's correct
            logger.debug(f"Chat data for id {chat_id}: {chat.to_json()}")

            logger.debug(f"Serving file {file_path} for chat_id: {chat_id}")
            response = send_from_directory(current_app.config["TMP_DIR"], filename)
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            return response

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error serving file")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    @file_bp.route("/file/<doc_id>", methods=["DELETE"])
    @token_required
    @handle_errors
    def delete_document(current_user: User, doc_id: str):
        try:
            file_metadata = FileMetadata.objects(id=doc_id).first()
            if not file_metadata:
                error_message, _ = log_error(
                    ValueError(f"File with doc_id {doc_id} not found"),
                    "Resource lookup",
                )
                return jsonify(create_error_response(error_message)), 404

            index_names = file_metadata.index_names
            file_url = file_metadata.s3_url

            logger.info(
                f"User {current_user.id} attempting to delete document {doc_id}"
            )
            logger.info(f"Current user is superadmin: {current_user.is_superadmin}")

            # Check permissions for each index
            can_delete = []
            for index_name in index_names:
                logger.info(f"Checking index_name: {index_name}")

                if current_user.is_superadmin:
                    logger.info(f"User {current_user.id} is superadmin.")
                    can_delete.append(True)
                elif index_name == current_user.personal_index_name:
                    logger.info(f"Index {index_name} is user's personal index.")
                    can_delete.append(True)
                else:
                    logger.info(
                        f"Checking organization permissions for index {index_name}"
                    )

                    # Check UserOrganization by index_name and user
                    user_organization = UserOrganization.objects(
                        index_name=index_name, user=current_user
                    ).first()

                    if user_organization:
                        logger.info(
                            f"User {current_user.id} role in {index_name}: {user_organization.role}"
                        )
                        if user_organization.role in ["admin", "editor"]:
                            can_delete.append(True)
                        else:
                            logger.info(
                                f"User {current_user.id} does not have admin or editor role for {index_name}"
                            )
                            can_delete.append(False)
                    else:
                        logger.info(
                            f"No UserOrganization found for user {current_user.id} and index {index_name}"
                        )
                        can_delete.append(False)

            logger.info(f"Final permission checks: {can_delete}")

            if not all(can_delete):
                error_message, _ = log_error(
                    ValueError("Insufficient permissions for one or more indices"),
                    "Permission check",
                )
                return jsonify(create_error_response(error_message)), 403

            logger.info(f"Index_names: {index_names}")

            # Use the delete_document method from file_service for each index
            results = []
            for index_name in index_names:
                result, status_code = asyncio.run(
                    file_service.delete_document(file_url, index_name)
                )
                logger.info(
                    f"Deletion result for index {index_name}: {result}, status code: {status_code}"
                )
                results.append(
                    {
                        "index_name": index_name,
                        "result": result,
                        "status_code": status_code,
                    }
                )

            # Check if all deletions were successful
            if all(result["status_code"] == 200 for result in results):
                # Delete the FileMetadata from the database
                file_metadata.delete()
                logger.info(
                    f"FileMetadata for document {doc_id} has been deleted from the database"
                )

                # Log the successful deletion
                ActionLog.log_action(
                    originating_user=current_user,
                    action_type="delete_doc",
                    target_documents=[file_metadata],
                    target_indices=[
                        IndexRegistry.objects.get(index_name=index_name)
                        for index_name in index_names
                    ],
                    description=f"Deleted document from multiple indices: {', '.join(index_names)}",
                )
                logger.info(
                    f"Document {doc_id} successfully deleted by user {current_user.id}"
                )
                return (
                    jsonify(
                        {
                            "message": "Document deleted successfully from all specified indices",
                            "results": results,
                        }
                    ),
                    200,
                )
            else:
                # If any deletion failed, return a partial success response
                logger.warning(
                    f"Partial success in deleting document {doc_id} by user {current_user.id}"
                )
                return (
                    jsonify(
                        {
                            "message": "Document deletion partially successful",
                            "results": results,
                        }
                    ),
                    207,
                )

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error deleting document")
            return jsonify(create_error_response(error_message, stack_trace)), 500

    @file_bp.route("/pdfjs/<path:filename>")
    def serve_pdfjs(filename):
        return send_from_directory("public/pdfjs", filename)

    @file_bp.route("/file/<doc_id>", methods=["GET"])
    @token_required
    @handle_errors
    def get_file_info(current_user: User, doc_id: str):
        try:
            file_metadata = FileMetadata.objects(id=doc_id).first()
            if not file_metadata:
                error_message, _ = log_error(
                    ValueError(f"File with doc_id {doc_id} not found"),
                    "Resource lookup",
                )
                return jsonify(create_error_response(error_message)), 404

            # Check if the file is soft-deleted
            if file_metadata.is_deleted:
                error_message, _ = log_error(
                    ValueError(f"File with doc_id {doc_id} has been deleted"),
                    "Resource lookup",
                )
                return jsonify(create_error_response(error_message)), 404

            # Check if the user has permission to access this file
            has_permission = False
            for index_name in file_metadata.index_names:
                if index_name == current_user.personal_index_name:
                    has_permission = True
                    break
                user_org = UserOrganization.objects(index_name=index_name).first()
                if user_org:
                    has_permission = True
                    break

            if not has_permission:
                error_message, _ = log_error(
                    ValueError(
                        f"User {current_user.id} does not have permission to access file {doc_id}"
                    ),
                    "Permission check",
                )
                return jsonify(create_error_response(error_message)), 403

            # Return the file information
            args = {
                "doc_id": str(file_metadata.id),
                "title": file_metadata.title,
                "visibility": file_metadata.visibility,
                "s3_url": file_metadata.s3_url,
                "index_names": file_metadata.index_names,
                "thumbnail_urls": file_metadata.thumbnail_urls,
                "filter_dimensions": file_metadata.filter_dimensions,
                "index_display_name": file_metadata.index_display_name,
            }
            if file_metadata.nominal_creator_name:
                args["nominal_creator_name"] = file_metadata.nominal_creator_name
            return jsonify(**args), 200

        except Exception as e:
            error_message, stack_trace = log_error(
                e, "Error retrieving file information"
            )
            return jsonify(create_error_response(error_message, stack_trace)), 500

    return file_bp
