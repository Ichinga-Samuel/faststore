"""In-memory storage engine.

Reads the entire upload into memory and returns the raw bytes via
:attr:`FileData.file`.  Useful for pipelines that need the payload
without touching the filesystem.
"""

from __future__ import annotations

from logging import getLogger
from pathlib import Path

from starlette.datastructures import UploadFile

from ..datastructures import FileData, FileField
from ..exceptions import StorageError, ValidationError
from ..util import normalize_relative_filename
from .storage_engine import StorageEngine

logger = getLogger(__name__)


class MemoryEngine(StorageEngine):
    """Store uploaded files in memory and return their bytes.

    The full file payload is available via :attr:`FileData.file` after
    a successful upload.
    """

    storage_name = "memory"

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        config = dict(file_field.config)
        await file.seek(0)

        try:
            payload = await file.read()
            size = len(payload)
            self.validate_size_limits(
                size=size,
                config=config,
                field_name=file_field.name,
                filename=file.filename,
            )
            filename = normalize_relative_filename(
                file.filename,
                sanitize=bool(config.get("sanitize_filename", True)),
            ).as_posix()
            return FileData(
                field_name=file_field.name,
                filename=filename,
                content_type=file.content_type,
                size=size,
                file=payload,
                message=f"{Path(filename).name} uploaded successfully",
                status=True,
                storage=self.storage_name,
            )
        except ValidationError:
            raise
        except Exception as err:
            logger.exception("Failed to save file to memory")
            raise StorageError(f"Unable to store '{file.filename}' in memory") from err
        finally:
            await file.close()
