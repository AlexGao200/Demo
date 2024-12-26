from flask import Blueprint, jsonify, request
from auth.utils import token_required
from utils.error_handlers import create_error_response, handle_errors
from loguru import logger
import tempfile
import os
from flask_mail import Message as MailMessage
from models.action_log import ActionLog
from models.organization import Organization
from models.pending import PendingDocument
from models.file_metadata import FileMetadata
from bson import ObjectId
from werkzeug.datastructures import FileStorage
import asyncio
from flask import current_app

from services.file_service import FileService


def create_petition_blueprint(chat_pdf, email_service, file_service: FileService):
    petition_bp = Blueprint("petition", __name__, url_prefix="/api/petition")

    s3_service = chat_pdf.s3_service

    @petition_bp.route("/public-doc-petition", methods=["POST"])
    @token_required
    @handle_errors
    def public_doc_petition(current_user):
        uploaded_file = request.files.get("file")
        title = request.form.get("title")
        organization_id = request.form.get("organization_id")

        if not uploaded_file:
            return jsonify(create_error_response("No file provided")), 400

        # Handle the organization reference
        if not organization_id or organization_id == "Miscellaneous":
            target_org = None
            organization_name = "Miscellaneous"
        else:
            target_org = Organization.objects(id=organization_id).first()
            if target_org:
                organization_name = target_org.name
            else:
                return jsonify(create_error_response("Invalid organization ID")), 400

        # Check if a file with the same title already exists in the public index
        if title:
            existing_document = FileMetadata.objects(
                title=title,
                index_names__in=[
                    "FIX_DOC_PETITION_ROUTES_INDEX"
                ],  # Note: this needs to be a list
            ).first()
            if existing_document:
                return (
                    jsonify(
                        create_error_response(
                            f"A document with the title '{title}' already exists in the public index."
                        )
                    ),
                    400,
                )

        # Save the file to S3
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            uploaded_file.save(tf.name)
            file_path = tf.name

        bucket_name = current_app.config["AWS_S3_PETITION_BUCKET_NAME"]
        file_url = s3_service.upload_file_to_s3(
            file_path, uploaded_file.filename, bucket_name
        )
        os.remove(file_path)

        if not file_url:
            return jsonify(create_error_response("Failed to upload file to S3")), 500

        # Store the document metadata in MongoDB with correct organization reference
        pending_document = PendingDocument(
            title=title,
            file_url=file_url,
            status="pending",  # Add required status field
            from_user=current_user,  # Add required user reference
            target_organization=target_org,  # Use the Organization object, not the name
        )
        pending_document.save()

        # Send an email to the admin with the document details
        admin_email = "info@acaceta.com"
        subject = f"New Document Uploaded for Review: {title or 'Untitled'}"
        body = f"A new document titled '{title or 'Untitled'}' has been uploaded by '{organization_name}'. You can review it at the following link: {file_url}"
        msg = MailMessage(subject, recipients=[admin_email], body=body)
        email_service.send(msg)

        return (
            jsonify(
                {
                    "message": "File uploaded successfully. Admin has been notified for review."
                }
            ),
            201,
        )

    @petition_bp.route("/get_pending_documents", methods=["GET"])
    @token_required
    @handle_errors
    def get_pending_documents(current_user):
        documents = PendingDocument.objects(status="pending")
        documents_list = []
        for doc in documents:
            try:
                org_name = (
                    doc.target_organization.name if doc.target_organization else "None"
                )
            except Exception:
                org_name = "None"

            documents_list.append(
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "file_url": doc.file_url,
                    "status": doc.status,
                    "organization_name": org_name,
                }
            )

        return jsonify(documents_list), 200

    @petition_bp.route("/reject_document", methods=["POST"])
    @token_required
    @handle_errors
    def reject_document(current_user):
        data = request.get_json()
        document_id = data.get("document_id")

        if not document_id:
            return jsonify(create_error_response("Document ID is required")), 400

        document = PendingDocument.objects(id=ObjectId(document_id)).first()

        if not document:
            return jsonify(create_error_response("Document not found")), 404

        petition_bucket = current_app.config["AWS_S3_PETITION_BUCKET_NAME"]

        # Delete the file from the petition bucket
        file_key = s3_service.extract_s3_key(document.file_url)
        s3_service.s3_client.delete_object(Bucket=petition_bucket, Key=file_key)
        logger.info(f"File deleted from petition bucket: {file_key}")

        # Remove the document from MongoDB
        document.delete()
        logger.info(f"Document {document_id} rejected and deleted from MongoDB")

        # Log the rejection action
        ActionLog.log_action(
            originating_user=current_user,
            action_type="reject_doc_petition",
            description=f"Rejected document petition: {document.title}",
        )

        return jsonify({"message": "Document rejected and deleted."}), 200

    @petition_bp.route("/approve_document", methods=["POST"])
    @token_required
    @handle_errors
    def approve_document(current_user):
        data = request.get_json()
        document_id = data.get("document_id")
        title = data.get("title")
        organization_name = data.get("index_namse")
        originating_user = data.get("originating_user")

        logger.info(f"Approve request received for document ID: {document_id}")
        if not document_id or not title:
            return (
                jsonify(create_error_response("Document ID and title are required")),
                400,
            )

        document = PendingDocument.objects(id=ObjectId(document_id)).first()
        if not document:
            return jsonify(create_error_response("Document not found")), 404

        logger.info(f"Document {document_id} found. Processing approval...")

        petition_bucket = current_app.config["AWS_S3_PETITION_BUCKET_NAME"]
        public_bucket = current_app.config["AWS_S3_BUCKET_NAME"]

        # Download the file from the petition bucket
        file_key = s3_service.extract_s3_key(document.file_url)
        logger.info(f"File key extracted: {file_key}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
            s3_service.s3_client.download_file(petition_bucket, file_key, tf.name)
            file_path = tf.name
            logger.info(f"File downloaded to temporary path: {file_path}")

        # Upload the file to the public bucket
        s3_service.s3_client.upload_file(file_path, public_bucket, file_key)
        logger.info(f"File uploaded to public bucket: {public_bucket}/{file_key}")

        with open(file_path, "rb") as file_content:
            file_storage = FileStorage(
                stream=file_content,
                filename=os.path.basename(file_key),
            )

            logger.info(
                f"Passing data to process_upload: org={organization_name}, title={title}"
            )

            results = asyncio.run(
                file_service.process_upload(
                    file_storage,
                    title,
                    "FIX_DOC_PETITION_ROUTES_INDEX",
                    "public",
                    originating_user,
                    [organization_name],
                    None,  # nominal_creator_name
                )
            )

        logger.info(f"process_upload result: {results}")

        if isinstance(results, dict) and "error" in results:
            logger.error(f"Error in process_upload: {results['error']}")
            os.remove(file_path)
            return jsonify(create_error_response(results["error"])), 400

        # Delete the file from the petition bucket after approval
        s3_service.s3_client.delete_object(Bucket=petition_bucket, Key=file_key)
        logger.info(f"File deleted from petition bucket: {file_key}")

        os.remove(file_path)

        # Remove the document from PendingDocument collection
        document.delete()
        logger.info(
            f"Document {document_id} approved and deleted from PendingDocument collection"
        )

        # Log the approval action
        ActionLog.log_action(
            originating_user=current_user,
            action_type="approve_doc_petition",
            description=f"Approved document petition: {title}",
            target_documents=(
                [results.get("file_metadata")]
                if isinstance(results, dict) and "file_metadata" in results
                else None
            ),
            target_indices=(
                [results.get("index")]
                if isinstance(results, dict) and "index" in results
                else None
            ),
        )

        return (
            jsonify(
                {"message": "Document approved, processed, and moved to public index."}
            ),
            200,
        )

    return petition_bp
