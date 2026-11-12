# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
from app.core.logging import get_logger
import os
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional

import aiofiles

logger = get_logger(__name__)


class StorageBackend(ABC):

    @abstractmethod
    async def upload(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> str:
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        pass

    @abstractmethod
    async def move(self, source_key: str, dest_key: str) -> bool:
        pass


class LocalStorageBackend(StorageBackend):

    def __init__(self, base_path: str = "/app/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        candidate = (self.base_path / key).resolve()
        base_resolved = self.base_path.resolve()
        if not str(candidate).startswith(str(base_resolved) + "/") and candidate != base_resolved:
            raise ValueError(f"Path traversal detected: key '{key}' resolves outside storage directory")
        return candidate

    async def upload(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> str:
        full_path = self._get_full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Read all data if it's a file-like object
        if hasattr(file_data, "read"):
            data = file_data.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
        else:
            data = file_data

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

        logger.info(f"Uploaded file to local storage: {key}")
        # Return web-accessible path, not filesystem path
        return f"/uploads/{key}"

    async def download(self, key: str) -> bytes:
        full_path = self._get_full_path(key)
        try:
            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {key}") from None

    async def delete(self, key: str) -> bool:
        full_path = self._get_full_path(key)
        try:
            full_path.unlink()
            logger.info(f"Deleted file from local storage: {key}")
            return True
        except FileNotFoundError:
            return False

    async def exists(self, key: str) -> bool:
        return self._get_full_path(key).exists()

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/uploads/{key}"

    async def move(self, source_key: str, dest_key: str) -> bool:
        source_path = self._get_full_path(source_key)
        dest_path = self._get_full_path(dest_key)

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(dest_path)
            logger.info(f"Moved file from {source_key} to {dest_key}")
            return True
        except FileNotFoundError:
            return False


class S3StorageBackend(StorageBackend):

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url

        # Lazy import boto3 - only when S3 backend is used
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install with: pip install boto3"
            ) from None

        config = Config(
            region_name=region,
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )

        client_kwargs = {"config": config}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self._client = boto3.client("s3", **client_kwargs)
        logger.info(f"Initialized S3 storage backend for bucket: {bucket}")

    async def upload(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> str:
        import asyncio

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        # Read data if file-like object
        if hasattr(file_data, "read"):
            data = file_data.read()
        else:
            data = file_data

        # Run S3 upload in thread pool (boto3 is synchronous)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                **extra_args,
            ),
        )

        logger.info(f"Uploaded file to S3: s3://{self.bucket}/{key}")
        return f"s3://{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.get_object(Bucket=self.bucket, Key=key),
        )
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        import asyncio
        from botocore.exceptions import ClientError

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_object(Bucket=self.bucket, Key=key),
            )
            logger.info(f"Deleted file from S3: s3://{self.bucket}/{key}")
            return True
        except ClientError as e:
            logger.error(
                f"Failed to delete S3 object {key}: {e}",
                extra={"error_type": type(e).__name__, "key": key},
            )
            return False

    async def exists(self, key: str) -> bool:
        import asyncio
        from botocore.exceptions import ClientError

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.head_object(Bucket=self.bucket, Key=key),
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            ),
        )
        return url

    async def move(self, source_key: str, dest_key: str) -> bool:
        import asyncio
        from botocore.exceptions import BotoCoreError, ClientError

        loop = asyncio.get_event_loop()
        try:
            # Copy to new location
            await loop.run_in_executor(
                None,
                lambda: self._client.copy_object(
                    Bucket=self.bucket,
                    CopySource={"Bucket": self.bucket, "Key": source_key},
                    Key=dest_key,
                ),
            )
            # Delete original
            await self.delete(source_key)
            logger.info(f"Moved S3 object from {source_key} to {dest_key}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to move S3 object: {e}")
            return False


class StorageService:

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    @staticmethod
    def generate_unique_key(
        prefix: str,
        filename: str,
        include_timestamp: bool = True,
    ) -> str:
        # Get extension
        ext = Path(filename).suffix.lower()

        # Generate random token
        token = secrets.token_urlsafe(16)

        # Build key
        if include_timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            key = f"{prefix}/{timestamp}_{token}{ext}"
        else:
            key = f"{prefix}/{token}{ext}"

        return key.lstrip("/")

    async def upload_file(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> tuple[str, str, int]:
        # Read data and compute hash
        if hasattr(file_data, "read"):
            data = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            data = file_data

        if isinstance(data, str):
            data = data.encode("utf-8")

        file_hash = hashlib.sha256(data).hexdigest()
        file_size = len(data)

        # Upload to backend
        from io import BytesIO
        storage_path = await self.backend.upload(BytesIO(data), key, content_type)

        return storage_path, file_hash, file_size

    async def download_file(self, key: str) -> bytes:
        return await self.backend.download(key)

    async def delete_file(self, key: str) -> bool:
        return await self.backend.delete(key)

    async def file_exists(self, key: str) -> bool:
        return await self.backend.exists(key)

    async def get_file_url(self, key: str, expires_in: int = 3600) -> str:
        return await self.backend.get_url(key, expires_in)

    async def move_to_trash(
        self,
        key: str,
        trash_prefix: str = "trash",
    ) -> Optional[str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = Path(key).name
        trash_key = f"{trash_prefix}/{timestamp}/{filename}"

        if await self.backend.move(key, trash_key):
            return trash_key
        return None


def get_storage_service() -> StorageService:
    backend_type = os.getenv("STORAGE_BACKEND", "local").lower()

    if backend_type == "s3":
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise ValueError("S3_BUCKET environment variable is required for S3 storage")

        backend = S3StorageBackend(
            bucket=bucket,
            region=os.getenv("S3_REGION", "us-east-1"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        logger.info(f"Using S3 storage backend: bucket={bucket}")
    else:
        base_path = os.getenv("STORAGE_LOCAL_PATH", "/app/uploads")
        backend = LocalStorageBackend(base_path=base_path)
        logger.info(f"Using local storage backend: path={base_path}")

    return StorageService(backend)


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = get_storage_service()
    return _storage_service
