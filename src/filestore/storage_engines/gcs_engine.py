"""Google Cloud Storage engine.

Uses ``google-cloud-storage`` to upload files to GCS.
The ``filestore[gcp]`` extra must be installed.
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
    from google.cloud import storage
except ModuleNotFoundError as err:  # pragma: no cover - exercised through lazy import behavior
    storage = None
    _GCS_IMPORT_ERROR = err
else:
    _GCS_IMPORT_ERROR = None


class GCSEngine(StorageEngine):
    """Persist uploads to Google Cloud Storage.

    Credentials are resolved from config, then Application Default
    Credentials.  Set ``endpoint_url`` to target emulators.
    """

    storage_name = "gcs"

    @staticmethod
    def _create_client(*, project: str = "", endpoint_url: str = "", credentials: Any = None):
        """Create a GCS client."""
        if storage is None:
            raise MissingDependencyError("Install filestore[gcp] to use GCSStorage") from _GCS_IMPORT_ERROR

        kwargs: dict[str, Any] = {}
        if project:
            kwargs["project"] = project
        if credentials is not None:
            kwargs["credentials"] = credentials
        if endpoint_url:
            kwargs["client_options"] = {"api_endpoint": endpoint_url}
        return storage.Client(**kwargs)

    @staticmethod
    def _build_url(bucket_name: str, key: str, endpoint_url: str | None, blob: Any) -> str:
        """Build a public URL for the uploaded object."""
        encoded_key = quote(key, safe="/")
        if endpoint_url:
            return f"{endpoint_url.rstrip('/')}/{bucket_name}/{encoded_key}"
        public_url = getattr(blob, "public_url", None)
        if public_url:
            return public_url
        return f"https://storage.googleapis.com/{bucket_name}/{encoded_key}"

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        config = dict(file_field.config)
        bucket_name = config.get("GCP_BUCKET_NAME") or os.environ.get("GCP_BUCKET_NAME")
        if not bucket_name:
            raise ConfigurationError("GCP_BUCKET_NAME must be provided for GCS uploads")

        project = config.get("GCP_PROJECT") or os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        credentials = config.get("GCP_CREDENTIALS")
        endpoint_url = config.get("endpoint_url") or ""
        prefix = await self.resolve_destination(file_field, file)
        relative_name = normalize_relative_filename(
            file.filename,
            sanitize=bool(config.get("sanitize_filename", True)),
        ).as_posix()
        key = join_cloud_key(prefix, relative_name)
        extra_args = dict(config.get("extra_args", {}))
        if not bool(config.get("overwrite", False)):
            extra_args.setdefault("if_generation_match", 0)

        client = self._create_client(project=project or "", endpoint_url=endpoint_url, credentials=credentials)

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
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(key)
            await asyncio.to_thread(
                blob.upload_from_file,
                file.file,
                rewind=True,
                size=size,
                content_type=file.content_type,
                **extra_args,
            )
            return FileData(
                field_name=file_field.name,
                filename=relative_name,
                content_type=file.content_type,
                size=size,
                url=self._build_url(bucket_name, key, endpoint_url or None, blob),
                metadata={"bucket": bucket_name, "key": key},
                message=f"{relative_name.rsplit('/', 1)[-1]} uploaded successfully",
                status=True,
                storage=self.storage_name,
            )
        except Exception as err:
            logger.exception("Failed to upload file to Google Cloud Storage")
            raise StorageError(f"Unable to store '{file.filename}' in Google Cloud Storage") from err
        finally:
            await file.close()
