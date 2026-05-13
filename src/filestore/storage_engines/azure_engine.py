"""Azure Blob Storage engine.

Uses ``azure-storage-blob`` (and optionally ``azure-identity``) to
upload files.  The ``filestore[azure]`` extra must be installed.
"""

from __future__ import annotations

import asyncio
import os
from logging import getLogger
from typing import Any

from starlette.datastructures import UploadFile

from ..datastructures import FileData, FileField
from ..exceptions import ConfigurationError, MissingDependencyError, StorageError
from ..util import join_cloud_key, normalize_relative_filename
from .storage_engine import StorageEngine

logger = getLogger(__name__)

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
except ModuleNotFoundError as err:  # pragma: no cover - exercised through lazy import behavior
    BlobServiceClient = None
    _AZURE_STORAGE_IMPORT_ERROR = err

    class ContentSettings:  # type: ignore[no-redef]
        def __init__(self, *, content_type: str | None = None, **_: Any):
            self.content_type = content_type

else:
    _AZURE_STORAGE_IMPORT_ERROR = None

try:
    from azure.identity import DefaultAzureCredential
except ModuleNotFoundError:  # pragma: no cover - fallback covered by config paths
    DefaultAzureCredential = None


class AzureBlobEngine(StorageEngine):
    """Persist uploads to Azure Blob Storage.

    Supports both connection-string and account-URL authentication.
    When neither a connection string nor an explicit credential is
    provided, ``DefaultAzureCredential`` is used automatically.
    """

    storage_name = "azure"

    @staticmethod
    def _create_client(*, connection_string: str = "", account_url: str = "", credential: Any = None):
        """Create an Azure ``BlobServiceClient``."""
        if BlobServiceClient is None:
            raise MissingDependencyError("Install filestore[azure] to use AzureStorage") from _AZURE_STORAGE_IMPORT_ERROR

        if connection_string:
            return BlobServiceClient.from_connection_string(connection_string)
        if not account_url:
            raise ConfigurationError(
                "AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL must be provided for Azure uploads"
            )
        return BlobServiceClient(account_url=account_url, credential=credential)

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        config = dict(file_field.config)
        container = config.get("AZURE_STORAGE_CONTAINER") or os.environ.get("AZURE_STORAGE_CONTAINER")
        if not container:
            raise ConfigurationError("AZURE_STORAGE_CONTAINER must be provided for Azure uploads")

        connection_string = config.get("AZURE_STORAGE_CONNECTION_STRING") or os.environ.get(
            "AZURE_STORAGE_CONNECTION_STRING"
        )
        account_url = config.get("AZURE_STORAGE_ACCOUNT_URL") or os.environ.get("AZURE_STORAGE_ACCOUNT_URL")
        credential = config.get("AZURE_STORAGE_CREDENTIAL")

        if credential is None and not connection_string and account_url:
            if DefaultAzureCredential is None:
                raise MissingDependencyError(
                    "Install filestore[azure] or provide AZURE_STORAGE_CONNECTION_STRING/AZURE_STORAGE_CREDENTIAL"
                )
            credential = DefaultAzureCredential()

        prefix = await self.resolve_destination(file_field, file)
        relative_name = normalize_relative_filename(
            file.filename,
            sanitize=bool(config.get("sanitize_filename", True)),
        ).as_posix()
        blob_name = join_cloud_key(prefix, relative_name)
        upload_kwargs = dict(config.get("extra_args", {}))
        upload_kwargs.setdefault("overwrite", bool(config.get("overwrite", False)))
        if file.content_type and "content_settings" not in upload_kwargs:
            upload_kwargs["content_settings"] = ContentSettings(content_type=file.content_type)

        client = self._create_client(
            connection_string=connection_string or "",
            account_url=account_url or "",
            credential=credential,
        )

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
            blob_client = client.get_blob_client(container=container, blob=blob_name)
            response = await asyncio.to_thread(
                blob_client.upload_blob,
                data=file.file,
                length=size,
                **upload_kwargs,
            )
            metadata = {"container": container, "blob": blob_name}
            etag = getattr(response, "etag", None) or getattr(response, "get", lambda *_: None)("etag")
            if etag:
                metadata["etag"] = etag
            return FileData(
                field_name=file_field.name,
                filename=relative_name,
                content_type=file.content_type,
                size=size,
                url=getattr(blob_client, "url", None),
                metadata=metadata,
                message=f"{relative_name.rsplit('/', 1)[-1]} uploaded successfully",
                status=True,
                storage=self.storage_name,
            )
        except Exception as err:
            logger.exception("Failed to upload file to Azure Blob Storage")
            raise StorageError(f"Unable to store '{file.filename}' in Azure Blob Storage") from err
        finally:
            await file.close()
