from collections.abc import AsyncIterator
from typing import BinaryIO, Protocol

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageProvider(Protocol):
    """Abstract storage provider interface."""

    async def upload_file(self, file_obj: BinaryIO, key: str) -> None: ...

    async def download_file(self, key: str) -> AsyncIterator[bytes]: ...

    async def delete_file(self, key: str) -> None: ...


class S3StorageProvider(StorageProvider):
    """Async S3 storage provider."""

    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.session = aioboto3.Session()

        self.client_config = {
            "endpoint_url": settings.S3_ENDPOINT_URL,
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION_NAME,
            "use_ssl": settings.S3_SECURE,
            "config": Config(
                signature_version="s3v4",
                connect_timeout=5,
                retries={
                    "max_attempts": 3,
                },
            ),
        }

    async def upload_file(self, file_obj: BinaryIO, key: str) -> None:
        try:
            async with self.session.client("s3", **self.client_config) as s3:
                await s3.upload_fileobj(
                    Fileobj=file_obj,
                    Bucket=self.bucket,
                    Key=key,
                )

        except ClientError as e:
            raise RuntimeError(f"Failed to upload '{key}'.") from e

    async def download_file(self, key: str) -> AsyncIterator[bytes]:
        try:
            async with self.session.client("s3", **self.client_config) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                body = response["Body"]
                while chunk := await body.read(1024 * 1024):
                    yield chunk

        except ClientError as e:
            raise RuntimeError(f"Failed to download '{key}'.") from e

    async def delete_file(self, key: str) -> None:
        try:
            async with self.session.client("s3", **self.client_config) as s3:
                await s3.delete_object(Bucket=self.bucket, Key=key)

        except ClientError as e:
            raise RuntimeError(f"Failed to delete '{key}'.") from e
