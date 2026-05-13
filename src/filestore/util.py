"""Utility functions used across the filestore package.

Provides helpers for async resolution, filename sanitization, path
manipulation, and a dynamic Pydantic model builder.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Awaitable, Iterable, Mapping, TypeVar
from urllib.parse import quote

from starlette.datastructures import UploadFile

if TYPE_CHECKING:
    from .main import FileStore

T = TypeVar("T")

_INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


async def maybe_await(value: T | Awaitable[T]) -> T:
    """Await *value* if it is awaitable, otherwise return it directly."""
    if inspect.isawaitable(value):
        return await value  # type: ignore[return-value]
    return value  # type: ignore[return-value]


def normalize_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a mutable copy of *config*, defaulting to an empty dict."""
    return dict(config or {})


def normalize_callable_list(value: Any) -> list[Any]:
    """Coerce *value* into a flat list of non-``None`` callables.

    Accepts a single callable, a list, a tuple, or ``None``.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value if item is not None]
    return [value]


def dedupe(values: Iterable[str]) -> list[str]:
    """Return *values* with duplicates and empty strings removed, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def sanitize_path_part(part: str, *, sanitize: bool = True) -> str:
    """Clean a single path component.

    Strips whitespace, rejects traversal segments (``..``), and optionally
    replaces non-alphanumeric characters.
    """
    cleaned = part.strip()
    if cleaned in {"", ".", ".."} or cleaned.endswith(":"):
        return ""
    if sanitize:
        cleaned = _INVALID_FILENAME_CHARS.sub("_", cleaned)
    cleaned = cleaned.strip()
    if cleaned in {"", ".", ".."}:
        return ""
    return cleaned


def normalize_relative_filename(
    filename: str | Path | None,
    *,
    sanitize: bool = True,
    default_name: str = "upload",
) -> Path:
    """Normalize *filename* into a safe, relative :class:`~pathlib.Path`.

    Back-slashes are converted to forward-slashes, traversal segments
    are removed, and (when *sanitize* is ``True``) unsafe characters are
    replaced with underscores.
    """
    raw_value = str(filename or default_name).replace("\\", "/")
    parts = []
    for part in PurePosixPath(raw_value).parts:
        cleaned = sanitize_path_part(part, sanitize=sanitize)
        if cleaned:
            parts.append(cleaned)
    if not parts:
        parts = [default_name]
    return Path(*parts)


def ensure_unique_path(path: Path) -> Path:
    """Return *path* if it doesn't exist, otherwise append a numeric suffix."""
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def as_absolute_directory(destination: str | Path | None) -> Path:
    """Resolve *destination* to an absolute directory path.

    Relative paths are resolved against :func:`Path.cwd`.
    """
    if destination is None:
        return Path.cwd()
    directory = Path(destination)
    if not directory.is_absolute():
        directory = Path.cwd() / directory
    return directory


def build_public_url(base_url: str | None, relative_path: Path | None) -> str | None:
    """Join *base_url* with *relative_path*, percent-encoding each segment."""
    if not base_url or relative_path is None:
        return None
    encoded_path = "/".join(quote(part) for part in relative_path.as_posix().split("/") if part)
    prefix = base_url.rstrip("/")
    return f"{prefix}/{encoded_path}" if encoded_path else prefix


def join_cloud_key(prefix: str | Path | None, relative_path: str | Path) -> str:
    """Build a cloud object key from *prefix* and *relative_path*.

    Normalizes separators and removes empty segments.
    """
    parts: list[str] = []
    if prefix:
        parts.extend(part for part in str(prefix).replace("\\", "/").split("/") if part)
    parts.extend(part for part in str(relative_path).replace("\\", "/").split("/") if part)
    return "/".join(parts)


# Keep old name as an alias for backward compatibility
join_s3_key = join_cloud_key


def file_size_hint(file: UploadFile | None) -> int | None:
    """Return the ``size`` attribute of *file* if available and non-negative."""
    if file is None:
        return None
    size = getattr(file, "size", None)
    return size if isinstance(size, int) and size >= 0 else None


def FileModel(obj: "FileStore", name: str = ""):
    """Return a Pydantic model mirroring the configured upload fields.

    Requires ``pydantic`` to be installed.  Raises :class:`ImportError`
    if it is not available.

    Args:
        obj: A :class:`FileStore` instance whose fields define the model schema.
        name: Optional model class name.  Defaults to ``<ClassName>FormModel``.
    """
    try:
        from pydantic import BaseModel, create_model
    except ImportError as err:
        raise ImportError(
            "pydantic is required for FileModel(). Install it with: pip install pydantic"
        ) from err

    body: dict[str, tuple[Any, Any]] = {}
    for item in obj.fields:
        if item.max_count > 1:
            annotation = list[UploadFile] if item.required else list[UploadFile] | None
        else:
            annotation = UploadFile if item.required else UploadFile | None
        default = ... if item.required else None
        body[item.name] = (annotation, default)
    model_name = name or f"{obj.__class__.__name__}FormModel"
    return create_model(model_name, **body, __base__=BaseModel)
