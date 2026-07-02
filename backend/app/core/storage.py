from abc import ABC, abstractmethod
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageProvider(ABC):
    """Abstract interface defining the decoupled Storage operations."""

    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, key: str) -> None:
        """Uploads a binary file stream to the storage store."""
        pass

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        """Downloads a file's raw payload bytes from the storage store."""
        pass

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Deletes a file and all its versions from the storage store."""
        pass


class S3StorageProvider(StorageProvider):
    """Concrete implementation of StorageProvider using AWS S3 / MinIO."""

    def __init__(self):
        # Configure client connection
        config = Config(
            signature_version="s3v4", connect_timeout=5, retries={"max_attempts": 3}
        )

        self.bucket_name = settings.S3_BUCKET_NAME

        # Initialize boto3 client
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
            use_ssl=settings.S3_SECURE,
            config=config,
        )

        # Ensure the configured bucket exists (extremely useful for local MinIO startup)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            # If 404, bucket does not exist, so we create it
            if error_code == "404" or "NoSuchBucket" in str(e):
                try:
                    if (
                        settings.S3_REGION_NAME
                        and settings.S3_REGION_NAME != "us-east-1"
                    ):
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": settings.S3_REGION_NAME
                            },
                        )
                    else:
                        self.client.create_bucket(Bucket=self.bucket_name)
                except ClientError as ce:
                    # Log or ignore if parallel creation occurs
                    pass

    def upload_file(self, file_obj: BinaryIO, key: str) -> None:
        try:
            self.client.upload_fileobj(
                Fileobj=file_obj, Bucket=self.bucket_name, Key=key
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {str(e)}") from e

    def download_file(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            raise RuntimeError(f"Failed to download file from S3: {str(e)}") from e

    def delete_file(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
        except ClientError as e:
            raise RuntimeError(f"Failed to delete file from S3: {str(e)}") from e


# Global storage client instance
_storage_client = None


def get_storage_client() -> StorageProvider:
    """Singleton getter for S3StorageProvider."""
    global _storage_client
    if _storage_client is None:
        _storage_client = S3StorageProvider()
    return _storage_client
