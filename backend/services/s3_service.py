import os
import urllib
import uuid

import boto3
from flask import current_app
from flask import jsonify
from loguru import logger
from ratelimit import limits, sleep_and_retry
from utils.error_handlers import log_error

# Initialize S3 client


class S3Service:
    def __init__(self):
        """
        Initialize the S3Service.

        Args:
            aws_access_key_id (str): AWS access key ID.
            aws_secret_access_key (str): AWS secret access key.
            region_name (str): AWS region name.
        """

        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

    @sleep_and_retry
    @limits(calls=5, period=60)
    def download_pdf(self, bucket: str, s3_url: str) -> str:
        """
        Download a PDF from S3.

        Args:
            bucket (str): S3 bucket name.
            s3_url (str): S3 URL of the PDF.

        Returns:
            str: Local file path of the downloaded PDF.

        Raises:
            ValueError: If s3_url is None or empty.
        """
        try:
            if not s3_url:
                raise ValueError("s3_url is None or empty")

            if not bucket:
                raise ValueError("Bucket is None or empty")

            logger.info(f"Downloading PDF from S3 URL: {s3_url}")

            tmp_dir = current_app.config.get("TMP_DIR")
            logger.info(f"Temporary directory: {tmp_dir}")
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)

            key = S3Service.extract_s3_key(s3_url)
            logger.info(f"Extracted S3 key: {key}")

            key = S3Service.validate_s3_key(key)
            logger.info(f"Validated S3 key: {key}")

            local_file_path = os.path.join(tmp_dir, os.path.basename(key))
            logger.info(f"Local file path: {local_file_path}")

            if os.path.exists(local_file_path):
                logger.info(f"File already exists locally: {local_file_path}")
                return local_file_path

            response = self.get_object(Bucket=bucket, Key=key)
            logger.info(f"S3 response received for key: {key}")
            logger.info(f"S3 response metadata: {response}")

            if response["Body"] is None:
                logger.error(f"S3 response body is None for key: {key}")
                raise ValueError(f"S3 response body is None for key: {key}")

            body_content = response["Body"].read()
            logger.trace(f"Body content type: {type(body_content)}")
            logger.trace(f"Body content length: {len(body_content)}")

            with open(local_file_path, "wb") as f:
                logger.info(f"Writing file to local path: {local_file_path}")
                f.write(body_content)

            logger.info(f"File downloaded successfully: {local_file_path}")
            return local_file_path
        except Exception as e:
            error_message, stack_trace = log_error(e, "Error downloading PDF")
            raise

    def get_object(self, Bucket: str, Key: str):
        """
        Get an object from S3.

        Args:
            Bucket (str): S3 bucket name.
            Key (str): S3 object key.

        Returns:
            Dict[str, Any]: S3 object data.

        Raises:
            ClientError: If the object does not exist or other S3 errors occur.
        """
        if not Bucket:
            raise ValueError("Bucket is None or empty")

        try:
            return self.s3_client.get_object(Bucket=Bucket, Key=Key)
        except self.s3_client.exceptions.NoSuchKey:
            error_message, stack_trace = log_error(
                self.s3_client.exceptions.NoSuchKey(),
                f"Error downloading file from S3: No such key {Key}",
            )
            return jsonify({"error": "The specified key does not exist"}), 404
        except Exception as e:
            error_message, stack_trace = log_error(e, "Error downloading file from S3")
            return jsonify({"error": error_message}), 500

    def upload_file_to_s3(self, file_path, filename=None, bucket_name=None):
        """
        Upload a file to Amazon S3.

        This method uploads a file to an S3 bucket, generating a unique S3 key for the file.
        If no bucket name is provided, it uses the default bucket specified in the environment variables.

        Args:
            file_path (str): The local path of the file to be uploaded.
            filename (str): The name to be used for the file in S3.
            bucket_name (str, optional): The name of the S3 bucket. If None, uses the default bucket from environment variables.

        Returns:
            str or None: The URL of the uploaded file in S3 if successful, None if an error occurs.

        Raises:
            ValueError: If AWS_S3_BUCKET_NAME or AWS_REGION environment variables are not set.

        Note:
            This method logs information about the upload process and any errors that occur.
        """
        if filename is None:
            filename = file_path.split("/")[-1]
        try:
            # Default to the general bucket if none is provided
            if not bucket_name:
                bucket_name = os.getenv("AWS_S3_BUCKET_NAME")

            aws_region = os.getenv("AWS_REGION")

            # Debug logging
            logger.info(f"Uploading file: {file_path} with filename: {filename}")
            logger.info(f"Bucket name: {bucket_name}")
            logger.info(f"AWS Region: {aws_region}")

            if not bucket_name or not aws_region:
                raise ValueError(
                    "AWS_S3_BUCKET_NAME or AWS_REGION environment variable is not set"
                )

            s3_key = f"{uuid.uuid4()}-{filename}"
            self.s3_client.upload_file(file_path, bucket_name, s3_key)
            file_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"

            logger.info(f"File uploaded to S3 with URL: {file_url}")

            return file_url

        except Exception as e:
            error_message, stack_trace = log_error(e, "Error uploading file to S3")
            logger.error(error_message)
            return None

    @staticmethod
    def extract_s3_key(s3_url: str) -> str:
        """Extract the S3 key from a given S3 URL."""
        parsed_url = urllib.parse.urlparse(s3_url)
        key = parsed_url.path.lstrip("/")
        key = urllib.parse.unquote(key)  # Unquote to handle URL-encoded characters
        key = key.replace("+", " ")  # Optional: Replace '+' with spaces if needed
        return key

    @staticmethod
    def validate_s3_key(key):
        """Validate the S3 key."""
        if not key or any(c in key for c in "\n\r\t"):
            raise ValueError(f"Invalid S3 key: {key}")
        return key

    def delete_file(self, bucket: str, key: str) -> None:
        """
        Delete a file from S3.

        Args:
            bucket (str): S3 bucket name.
            key (str): S3 object key.

        Raises:
            ValueError: If bucket or key is None/empty, or if key is invalid.
            ClientError: If S3 operation fails (e.g., NoSuchKey).
            Exception: For other unexpected errors.
        """
        if not bucket:
            raise ValueError("Bucket is None or empty")
        if not key:
            raise ValueError("Key is None or empty")

        key = self.validate_s3_key(key)
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(
                f"Successfully deleted file from S3. Bucket: {bucket}, Key: {key}"
            )
        except Exception as e:
            error_message, _ = log_error(e, "Error deleting file from S3")
            raise
