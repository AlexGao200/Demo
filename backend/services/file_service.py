from models.file_metadata import FileMetadata, ProcessingStatus
from models.user import User
import tempfile
from utils.error_handlers import log_error
from loguru import logger
import fitz
import os
from PIL import Image
import urllib.parse
from services.document_ingestion_service import DocumentProcessor
from elasticsearch import NotFoundError
from threading import Thread
from datetime import datetime, timezone
import asyncio


class FileService:
    def __init__(
        self, s3_service, document_processor: DocumentProcessor, elasticsearch_client
    ):
        self.s3_service = s3_service
        self.document_processor = document_processor
        self.elasticsearch_client = elasticsearch_client

    async def process_upload(
        self,
        uploaded_file,
        title,
        index_names,
        file_visibility,
        user_id,
        nominal_creator_name,
        filter_dimensions,
    ):
        try:
            # Check for existing document
            existing_document = FileMetadata.objects(
                title=title, index_names__contains=index_names
            ).first()
            if existing_document:
                error_message, _ = log_error(
                    ValueError(
                        f"A document with the title '{title}' already exists in the '{index_names}' index."
                    ),
                    "Document title conflict check",
                )
                return {"error": error_message}

            # Phase 1: Quick initial upload (0.0 -> 0.1)
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                uploaded_file.save(tf.name)
                file_path = tf.name

            # Upload to S3
            file_url = self.s3_service.upload_file_to_s3(
                file_path, uploaded_file.filename
            )
            if file_url is None:
                error_message, _ = log_error(
                    Exception("Failed to upload file to S3"), "S3 upload attempt"
                )
                return {"error": error_message}, 500

            file_url = urllib.parse.quote(file_url, safe=":/")
            logger.info(f"type of index_names: {index_names}")
            # Create initial metadata with pending status
            metadata = FileMetadata(
                name=uploaded_file.filename,
                s3_url=file_url,
                document_hash="pending",  # Will be updated during processing
                title=title,
                index_names=index_names,
                visibility=file_visibility,
                originating_user=User.objects(id=user_id).first(),
                nominal_creator_name=nominal_creator_name,
                index_display_name=index_names[0],  # Simplified for now
                filter_dimensions=filter_dimensions,
                processing_status=ProcessingStatus.PROCESSING,
                processing_progress=0.1,
                processing_step="Initial upload complete",
                processing_started_at=datetime.now(timezone.utc),
            ).save()

            # Phase 2: Start background processing
            Thread(
                target=self._process_document_background,
                args=(file_path, metadata.id, uploaded_file.filename),
                daemon=True,
            ).start()

            # Return immediately with document ID
            return {"message": "File upload started", "doc_id": str(metadata.id)}

        except Exception as e:
            error_message, _ = log_error(e, "Upload initialization")
            return {"error": error_message}, 500

    def _process_document_background(self, file_path, doc_id, filename):
        try:
            metadata = FileMetadata.objects(id=doc_id).first()

            # Generate thumbnails (0.1 -> 0.2)
            metadata.update_progress(0.15, "Generating thumbnails")
            thumbnails = self.generate_pdf_thumbnails(file_path)

            thumbnail_urls = []
            if thumbnails:
                for j, img in enumerate(thumbnails):
                    thumbnail_file_path = f"{file_path}_thumb_{j}.jpg"
                    img.save(thumbnail_file_path)
                    thumbnail_url = self.s3_service.upload_file_to_s3(
                        thumbnail_file_path, f"{filename}_thumb_{j}.jpg"
                    )
                    if thumbnail_url:
                        thumbnail_url = urllib.parse.quote(thumbnail_url, safe=":/")
                        thumbnail_urls.append(thumbnail_url)
                    os.remove(thumbnail_file_path)
                metadata.update_progress(0.2, "Thumbnails generated")

            # Document processing and ingestion (0.2 -> 1.0)
            try:
                metadata.update_progress(0.3, "Processing document text")

                # Run async ingest in the background thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                ingest_result = loop.run_until_complete(
                    self.document_processor.ingest(
                        file_path=file_path,
                        file_url=metadata.s3_url,
                        title=metadata.title,
                        thumbnail_urls=thumbnail_urls,
                        index_names=metadata.index_names,
                        file_visibility=metadata.visibility,
                        originating_user_id=str(metadata.originating_user.id),
                        nominal_creator_name=metadata.nominal_creator_name,
                        filter_dimensions=metadata.filter_dimensions,
                        progress_callback=lambda progress,
                        step: metadata.update_progress(
                            0.3 + (progress * 0.7),  # Scale remaining 70% of progress
                            step,
                        ),
                    )
                )
                loop.close()

                if ingest_result:
                    metadata.processing_status = ProcessingStatus.COMPLETED
                    metadata.processing_progress = 1.0
                    metadata.processing_step = "Processing complete"
                    metadata.processing_completed_at = datetime.now(timezone.utc)
                    metadata.save()
                else:
                    raise Exception("Document ingestion failed")

            except Exception as e:
                logger.error(f"Error during document ingestion: {str(e)}")
                metadata.processing_status = ProcessingStatus.FAILED
                metadata.processing_error = str(e)
                metadata.save()
                raise

            finally:
                # Cleanup
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing temporary file: {str(e)}")

        except Exception as e:
            logger.error(f"Background processing error: {str(e)}")
            try:
                metadata = FileMetadata.objects(id=doc_id).first()
                metadata.processing_status = ProcessingStatus.FAILED
                metadata.processing_error = str(e)
                metadata.save()
            except Exception as inner_e:
                logger.error(f"Error updating metadata after failure: {str(inner_e)}")

    def generate_pdf_thumbnails(self, pdf_path):
        try:
            pdf_document = fitz.open(pdf_path)
            thumbnails = []

            for page_num in range(min(2, len(pdf_document))):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((900, 1600))
                thumbnails.append(img)

            return thumbnails

        except Exception as e:
            error_message, _ = log_error(e, "PDF thumbnail generation")
            return []

    async def delete_document(self, file_url, index_name):
        try:
            # Delete document from MongoDB
            document = FileMetadata.objects(s3_url=file_url).first()
            if not document:
                error_message, _ = log_error(
                    Exception(
                        f"Document not found in MongoDB for file_url: {file_url}"
                    ),
                    "MongoDB document deletion",
                )
                return {"error": error_message}, 404

            document_title = document.title
            document.delete()
            logger.info(f"Document '{document_title}' deleted from MongoDB")

            # Delete document from Elasticsearch
            query = {"query": {"match": {"metadata.file_url": file_url}}}
            try:
                delete_result = self.elasticsearch_client.delete_by_query(
                    index=index_name, body=query
                )
                if delete_result["deleted"] == 0:
                    logger.warning(
                        f"No documents found in Elasticsearch for deletion. Index: {index_name}, file_url: {file_url}"
                    )
                else:
                    logger.info(
                        f"Document deleted from Elasticsearch. Index: {index_name}, Deleted count: {delete_result['deleted']}"
                    )
            except NotFoundError:
                logger.warning(f"Index {index_name} not found in Elasticsearch")
            except Exception as es_error:
                error_message, _ = log_error(
                    es_error, "Elasticsearch document deletion"
                )
                return {"error": error_message}, 500

            # Delete file from S3
            try:
                s3_key = self.s3_service.extract_s3_key(file_url)
                bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
                # Remove hyphens from bucket name for S3 operations
                s3_bucket_name = bucket_name.replace("-", "")
                self.s3_service.s3_client.delete_object(
                    Bucket=s3_bucket_name, Key=s3_key
                )
                logger.info(
                    f"Document deleted from S3. Bucket: {s3_bucket_name}, Key: {s3_key}"
                )
            except Exception as s3_error:
                error_message, _ = log_error(s3_error, "S3 document deletion")
                return {"error": error_message}, 500

            logger.info(
                f"Document '{document_title}' deleted successfully from index '{index_name}'"
            )
            return {
                "message": "Document deleted successfully",
                "title": document_title,
            }, 200

        except Exception as e:
            error_message, _ = log_error(e, "Document deletion process")
            return {"error": error_message}, 500
