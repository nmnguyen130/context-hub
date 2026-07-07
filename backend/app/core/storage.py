from abc import ABC, abstractmethod
from typing import BinaryIO

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageProvider(ABC):
    """Abstract storage provider interface."""

    @abstractmethod
    async def upload_file(self, file_obj: BinaryIO, key: str) -> None: ...

    @abstractmethod
    async def download_file(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete_file(self, key: str) -> None: ...


class S3StorageProvider(StorageProvider):
    """S3 / MinIO storage provider."""

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.session = aioboto3.Session()
        self.config_kwargs = {
            "endpoint_url": settings.S3_ENDPOINT_URL,
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION_NAME,
            "use_ssl": settings.S3_SECURE,
            "config": Config(
                signature_version="s3v4",
                connect_timeout=5,
                retries={"max_attempts": 3},
            ),
        }

    async def ensure_bucket_exists(self) -> None:
        try:
            async with self.session.client("s3", **self.config_kwargs) as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
                return
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket"}:
                raise

        try:
            kwargs = {"Bucket": self.bucket_name}
            if settings.S3_REGION_NAME and settings.S3_REGION_NAME != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.S3_REGION_NAME
                }

            async with self.session.client("s3", **self.config_kwargs) as s3:
                await s3.create_bucket(**kwargs)
        except ClientError:
            # Ignore race condition when another instance creates the bucket.
            pass

    async def upload_file(self, file_obj: BinaryIO, key: str) -> None:
        try:
            async with self.session.client("s3", **self.config_kwargs) as s3:
                await s3.upload_fileobj(
                    Fileobj=file_obj,
                    Bucket=self.bucket_name,
                    Key=key,
                )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload '{key}'.") from e

    async def download_file(self, key: str) -> bytes:
        try:
            async with self.session.client("s3", **self.config_kwargs) as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
        except ClientError as e:
            raise RuntimeError(f"Failed to download '{key}'.") from e

    async def delete_file(self, key: str) -> None:
        try:
            async with self.session.client("s3", **self.config_kwargs) as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
        except ClientError as e:
            raise RuntimeError(f"Failed to delete '{key}'.") from e
