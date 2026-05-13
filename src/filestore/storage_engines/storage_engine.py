"""Abstract base class for all storage backends.

Every engine must implement :meth:`upload` and return a populated
:class:`~filestore.datastructures.FileData`.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Mapping

from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

from ..datastructures import FileData, FileField
from ..exceptions import ValidationError
from ..util import file_size_hint, maybe_await


class StorageEngine(ABC):
    """Base class for all storage backends.

    Subclasses must implement :meth:`upload` to persist a file and
    return a :class:`FileData` result.

    Attributes:
        storage_name: Human-readable name of this backend (e.g. ``"local"``).
        default_chunk_size: Default read/write chunk size in bytes.
    """

    storage_name = "storage"
    default_chunk_size = 1024 * 1024  # 1 MiB

    def __init__(self, *, request: Request, form: FormData):
        self.form = form
        self.request = request

    async def resolve_destination(self, file_field: FileField, file: UploadFile) -> str | None:
        """Resolve the upload destination from config, supporting callables."""
        destination = file_field.config.get("destination")
        if callable(destination):
            destination = await maybe_await(destination(self.request, self.form, file_field.name, file))
        if destination is None:
            return None
        return str(destination)

    @classmethod
    def get_chunk_size(cls, config: Mapping[str, Any]) -> int:
        """Return the chunk size from *config*, falling back to the class default."""
        chunk_size = int(config.get("chunk_size", cls.default_chunk_size) or cls.default_chunk_size)
        return max(chunk_size, 1)

    @staticmethod
    def get_size_hint(file: UploadFile) -> int | None:
        """Return the reported size of *file*, or ``None``."""
        return file_size_hint(file)

    @staticmethod
    def detect_stream_size(file_obj: Any) -> int:
        """Determine the size of a seekable stream without consuming it."""
        position = file_obj.tell()
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(position)
        return size

    @staticmethod
    def validate_size_limits(
        *,
        size: int,
        config: Mapping[str, Any],
        field_name: str,
        filename: str | None,
        final: bool = True,
    ) -> None:
        """Raise :class:`ValidationError` if *size* violates configured limits.

        Args:
            size: Current byte count.
            config: Config dict containing ``max_file_size`` / ``min_file_size``.
            field_name: Field name for error messages.
            filename: Filename for error messages.
            final: When ``False``, skip the minimum-size check (useful
                during streaming writes).
        """
        max_size = config.get("max_file_size")
        if max_size is not None and size > int(max_size):
            raise ValidationError(
                f"File '{filename or 'upload'}' in field '{field_name}' exceeds the maximum size of {int(max_size)} bytes"
            )
        min_size = config.get("min_file_size")
        if final and min_size is not None and size < int(min_size):
            raise ValidationError(
                f"File '{filename or 'upload'}' in field '{field_name}' is smaller than the minimum size of {int(min_size)} bytes"
            )

    @abstractmethod
    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Persist *file* and return a :class:`FileData` with the result."""
