"""Amazon S3 storage engine.

Uses ``boto3`` to upload files to S3-compatible object stores.
The ``filestore[s3]`` extra must be installed.
"""

from __future__ import annotations

import asyncio
import os
from logging import getLogger
from typing import Any
from urllib.parse import quote

from starlette.datastructures import UploadFile

from ..datastructures import FileData, FileField
from ..exceptions import ConfigurationError, MissingDependencyError, StorageError
from ..util import join_cloud_key, normalize_relative_filename
from .storage_engine import StorageEngine

logger = getLogger(__name__)

try:
    import boto3
    from botocore.client import BaseClient
except ModuleNotFoundError as err:  # pragma: no cover - covered via lazy import path
    boto3 = None
    BaseClient = Any
    _BOTO3_IMPORT_ERROR = err
else:
    _BOTO3_IMPORT_ERROR = None


class S3Engine(StorageEngine):
    """Persist uploads to Amazon S3 or any S3-compatible service.

    Credentials are resolved from config, then environment variables,
    then the default boto3 credential chain.
    """

    storage_name = "s3"

    @staticmethod
    def _create_client(*, region_name: str = "", endpoint_url: str = "") -> "BaseClient":
        """Create a fresh ``boto3`` S3 client.

        Unlike a cached client, this respects credential changes between
        requests and avoids shared mutable state across concurrent uploads.
        """
        if boto3 is None:
            raise MissingDependencyError("Install filestore[s3] to use S3Storage") from _BOTO3_IMPORT_ERROR
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": region_name or os.environ.get("AWS_DEFAULT_REGION"),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        return boto3.client(**kwargs)

    @staticmethod
    def _build_url(bucket: str, key: str, region: str | None, endpoint_url: str | None) -> str:
        """Build a public URL for the uploaded object."""
        encoded_key = quote(key, safe="/")
        if endpoint_url:
            return f"{endpoint_url.rstrip('/')}/{bucket}/{encoded_key}"
        if region:
            return f"https://{bucket}.s3.{region}.amazonaws.com/{encoded_key}"
        return f"https://{bucket}.s3.amazonaws.com/{encoded_key}"

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        config = dict(file_field.config)
        bucket = config.get("AWS_BUCKET_NAME") or os.environ.get("AWS_BUCKET_NAME")
        if not bucket:
            raise ConfigurationError("AWS_BUCKET_NAME must be provided for S3 uploads")

        region = config.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        endpoint_url = config.get("endpoint_url") or ""
        prefix = await self.resolve_destination(file_field, file)
        relative_name = normalize_relative_filename(
            file.filename,
            sanitize=bool(config.get("sanitize_filename", True)),
        ).as_posix()
        key = join_cloud_key(prefix, relative_name)
        extra_args = dict(config.get("extra_args", {}))
        client = self._create_client(region_name=region or "", endpoint_url=endpoint_url)

        size = self.get_size_hint(file)
        if size is None:
            size = await asyncio.to_thread(self.detect_stream_size, file.file)
        self.validate_size_limits(
            size=size,
            config=config,
            field_name=file_field.name,
            filename=file.filename,
        )

        await file.seek(0)

        try:
            response = await asyncio.to_thread(
                client.put_object,
                Body=file.file,
                Bucket=bucket,
                Key=key,
                **extra_args,
            )
            metadata = response.get("ResponseMetadata", {})
            status_code = metadata.get("HTTPStatusCode", 0)
            status = status_code in {200, 201}
            short_name = relative_name.rsplit("/", 1)[-1]
            message = f"{short_name} uploaded successfully" if status else f"Failed to upload {relative_name}"
            return FileData(
                field_name=file_field.name,
                filename=relative_name,
                content_type=file.content_type,
                size=size,
                url=self._build_url(bucket, key, region, endpoint_url or None),
                metadata={"bucket": bucket, "key": key, **metadata},
                message=message,
                status=status,
                storage=self.storage_name,
            )
        except Exception as err:
            logger.exception("Failed to upload file to S3")
            raise StorageError(f"Unable to store '{file.filename}' in S3") from err
        finally:
            await file.close()
