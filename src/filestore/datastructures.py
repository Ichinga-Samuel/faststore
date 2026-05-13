"""Core data structures for the filestore package.

Defines the typed configuration dictionary, declarative field descriptors,
per-file result objects, and the aggregate store that wraps an entire
upload request.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping, Type, TypedDict, TypeVar

from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

if TYPE_CHECKING:
    from .storage_engines.storage_engine import StorageEngine

T = TypeVar("T")

Callback = Callable[[Request, FormData, str, UploadFile], T | Awaitable[T]]
"""Signature shared by all per-file callbacks: ``(request, form, field_name, file) -> T``."""

FilterCallback = Callback[bool | str]
"""Filter callback.  Return ``True`` to accept, ``False`` or a message string to reject."""

MetadataValue = Mapping[str, Any] | Callback[Mapping[str, Any]]
"""Static metadata dict or a callback that produces one."""

FilenameValue = str | Path | UploadFile | Callback[str | Path | UploadFile | None]
"""A fixed filename, or a callback that resolves one at upload time."""

DestinationValue = str | Path | Callback[str | Path]
"""Upload directory / cloud prefix, or a callback that resolves one."""


class Config(TypedDict, total=False):
    """Typed configuration accepted by :class:`FileStore` and :class:`FileField`.

    All keys are optional.  Backend-specific keys (``AWS_*``, ``GCP_*``,
    ``AZURE_*``) are only relevant for the matching storage engine.
    """

    # --- general ---
    destination: DestinationValue
    filters: list[FilterCallback] | FilterCallback
    max_files: int
    max_fields: int
    max_part_size: int
    filename: FilenameValue
    extra_args: Mapping[str, Any]
    metadata: MetadataValue

    # --- validation ---
    max_file_size: int
    min_file_size: int
    allowed_extensions: list[str] | set[str] | tuple[str, ...]
    allowed_content_types: list[str] | set[str] | tuple[str, ...]

    # --- local engine ---
    chunk_size: int
    overwrite: bool
    sanitize_filename: bool
    base_url: str

    # --- cloud common ---
    endpoint_url: str

    # --- AWS S3 ---
    AWS_DEFAULT_REGION: str
    AWS_BUCKET_NAME: str

    # --- Google Cloud ---
    GCP_BUCKET_NAME: str
    GCP_PROJECT: str
    GCP_CREDENTIALS: Any

    # --- Azure Blob ---
    AZURE_STORAGE_CONTAINER: str
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_ACCOUNT_URL: str
    AZURE_STORAGE_CREDENTIAL: Any

    # --- engine override ---
    storage_engine: "StorageEngine"
    StorageEngine: Type["StorageEngine"]


@dataclass(slots=True)
class FileField:
    """Declarative upload-field definition.

    Attributes:
        name: The HTML form-field name to read from the multipart body.
        max_count: Maximum number of files accepted for this field.
        required: When ``True``, the upload request fails if no files
            are provided for this field.
        config: Per-field configuration that overrides store-level config.
    """

    name: str
    max_count: int = 1
    required: bool = False
    config: Config | Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("FileField.name must not be empty")
        if self.max_count < 1:
            raise ValueError("FileField.max_count must be at least 1")
        self.config = dict(self.config or {})

    def __repr__(self) -> str:
        return (
            f"FileField(name={self.name!r}, max_count={self.max_count}, "
            f"required={self.required})"
        )


@dataclass(slots=True)
class FileData:
    """Normalized result for a single uploaded file.

    Attributes:
        field_name: The form-field this file was submitted under.
        path: Absolute local path (local engine only).
        url: Public URL for retrieving the file.
        status: ``True`` when the file was persisted successfully.
        content_type: MIME type reported by the client.
        filename: Final stored filename (may differ from the original).
        original_filename: Filename as submitted by the client.
        size: File size in bytes.
        file: Raw bytes (memory engine only).
        metadata: Arbitrary per-file metadata from callbacks or backends.
        error: Human-readable error message when ``status`` is ``False``.
        message: Human-readable status message.
        storage: Name of the storage backend that handled this file.
    """

    field_name: str
    path: Path | None = None
    url: str | None = None
    status: bool = False
    content_type: str | None = None
    filename: str | None = None
    original_filename: str | None = None
    size: int | None = None
    file: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    message: str | None = None
    storage: str | None = None

    @property
    def location(self) -> str | Path | None:
        """Return the most useful persisted location for the file.

        Prefers ``url`` over ``path``.
        """
        return self.url or self.path

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation.

        Converts ``Path`` objects to strings and omits raw ``bytes`` to
        keep the output serializable.
        """
        data = asdict(self)
        if self.path is not None:
            data["path"] = str(self.path)
        # Omit raw bytes — not JSON-serializable
        if self.file is not None:
            data["file"] = f"<{len(self.file)} bytes>"
        return data

    def __repr__(self) -> str:
        status = "ok" if self.status else "failed"
        return (
            f"FileData(field={self.field_name!r}, filename={self.filename!r}, "
            f"status={status}, size={self.size})"
        )


@dataclass(slots=True)
class Store:
    """Aggregated response for all processed upload fields.

    This is the object returned by the FastAPI dependency.

    Attributes:
        files: Per-field lists of :class:`FileData` results.
        error: First error message, if any.
        message: Summary status message.
        status: ``True`` when every file was uploaded successfully.
        errors: All error messages collected during the upload.
        messages: All informational messages.
    """

    files: dict[str, list[FileData]] = field(default_factory=dict)
    error: str | None = None
    message: str | None = None
    status: bool = True
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def add(self, file_data: FileData) -> None:
        """Append a :class:`FileData` result to the store."""
        self.files.setdefault(file_data.field_name, []).append(file_data)
        if file_data.error:
            self.errors.append(file_data.error)
        if file_data.message:
            self.messages.append(file_data.message)

    # --- computed properties ---

    @property
    def flat_files(self) -> list[FileData]:
        """All files across every field in a single list."""
        return [file_data for items in self.files.values() for file_data in items]

    @property
    def successful_files(self) -> list[FileData]:
        """Only files that were persisted successfully."""
        return [file_data for file_data in self.flat_files if file_data.status]

    @property
    def failed_files(self) -> list[FileData]:
        """Only files that failed validation or persistence."""
        return [file_data for file_data in self.flat_files if not file_data.status]

    @property
    def total_files(self) -> int:
        """Total number of processed files (successful + failed)."""
        return len(self.flat_files)

    @property
    def total_size(self) -> int:
        """Sum of sizes for all successfully uploaded files."""
        return sum(f.size for f in self.successful_files if f.size is not None)

    def first(self, field_name: str) -> FileData | None:
        """Return the first :class:`FileData` for *field_name*, or ``None``."""
        files = self.files.get(field_name, [])
        return files[0] if files else None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return {
            "files": {
                field_name: [file_data.to_dict() for file_data in items]
                for field_name, items in self.files.items()
            },
            "error": self.error,
            "message": self.message,
            "status": self.status,
            "errors": list(self.errors),
            "messages": list(self.messages),
        }

    def __repr__(self) -> str:
        return (
            f"Store(status={self.status}, total={self.total_files}, "
            f"ok={len(self.successful_files)}, failed={len(self.failed_files)})"
        )
