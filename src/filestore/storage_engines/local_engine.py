"""Local filesystem storage engine.

Writes files atomically via a temporary file + rename pattern and
supports collision-free naming when ``overwrite`` is ``False``.
"""

from __future__ import annotations

import asyncio
from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from uuid import uuid4

from starlette.datastructures import UploadFile

from ..datastructures import FileData, FileField
from ..exceptions import StorageError, ValidationError
from ..util import as_absolute_directory, build_public_url, ensure_unique_path, normalize_relative_filename
from .storage_engine import StorageEngine

logger = getLogger(__name__)


class LocalEngine(StorageEngine):
    """Persist uploads to the local filesystem.

    Files are written atomically: data is first written to a temporary
    file in the target directory, then renamed into place.  When
    ``overwrite`` is ``False`` (the default), a numeric suffix is
    appended to avoid overwriting existing files.
    """

    storage_name = "local"

    @classmethod
    def _write_file(
        cls,
        *,
        source: BinaryIO,
        target: Path,
        chunk_size: int,
        config: dict,
        field_name: str,
        filename: str | None,
    ) -> int:
        """Write *source* to *target* in chunks, validating size limits.

        This runs in a thread via :func:`asyncio.to_thread`.
        """
        bytes_written = 0
        with target.open("wb") as handle:
            while chunk := source.read(chunk_size):
                bytes_written += len(chunk)
                cls.validate_size_limits(
                    size=bytes_written,
                    config=config,
                    field_name=field_name,
                    filename=filename,
                    final=False,
                )
                handle.write(chunk)
        cls.validate_size_limits(
            size=bytes_written,
            config=config,
            field_name=field_name,
            filename=filename,
            final=True,
        )
        return bytes_written

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        config = dict(file_field.config)
        relative_name = normalize_relative_filename(
            file.filename,
            sanitize=bool(config.get("sanitize_filename", True)),
        )
        destination = as_absolute_directory(await self.resolve_destination(file_field, file))
        destination.mkdir(parents=True, exist_ok=True)
        final_path = destination / relative_name
        final_path.parent.mkdir(parents=True, exist_ok=True)

        if not bool(config.get("overwrite", False)):
            final_path = ensure_unique_path(final_path)

        temp_path = final_path.with_name(f".{final_path.name}.{uuid4().hex}.tmp")
        await file.seek(0)

        try:
            with NamedTemporaryFile(delete=False, dir=final_path.parent) as temp_file:
                temp_path = Path(temp_file.name)
            size = await asyncio.to_thread(
                self._write_file,
                source=file.file,
                target=temp_path,
                chunk_size=self.get_chunk_size(config),
                config=config,
                field_name=file_field.name,
                filename=file.filename,
            )
            temp_path.replace(final_path)
            relative_path = final_path.relative_to(destination)
            return FileData(
                field_name=file_field.name,
                filename=relative_path.as_posix(),
                content_type=file.content_type,
                size=size,
                path=final_path.resolve(),
                url=build_public_url(config.get("base_url"), relative_path),
                metadata={"relative_path": relative_path.as_posix()},
                message=f"{relative_path.name} uploaded successfully",
                status=True,
                storage=self.storage_name,
            )
        except ValidationError:
            temp_path.unlink(missing_ok=True)
            raise
        except Exception as err:
            temp_path.unlink(missing_ok=True)
            logger.exception("Failed to save file to local storage")
            raise StorageError(f"Unable to store '{file.filename}' in field '{file_field.name}'") from err
        finally:
            await file.close()
