"""filestore — Production-ready file upload toolkit for FastAPI.

Provides pluggable storage backends (local, memory, S3, GCS, Azure)
with a clean dependency-injection API, file validation, callbacks,
and rich per-file results.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .datastructures import Config, FileData, FileField, Store
from .exceptions import ConfigurationError, FileStoreError, MissingDependencyError, StorageError, ValidationError
from .localstorage import LocalStorage
from .main import FileStore
from .memorystorage import MemoryStorage
from .storage_engines import LocalEngine, MemoryEngine, StorageEngine
from .util import FileModel

try:
    __version__ = version("filestore")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
    __version__ = "0.0.0"

__all__ = [
    "AzureBlobEngine",
    "AzureStorage",
    "Config",
    "ConfigurationError",
    "FileData",
    "FileField",
    "FileModel",
    "FileStore",
    "FileStoreError",
    "GCSEngine",
    "GCSStorage",
    "LocalEngine",
    "LocalStorage",
    "MemoryEngine",
    "MemoryStorage",
    "MissingDependencyError",
    "S3Engine",
    "S3Storage",
    "StorageEngine",
    "StorageError",
    "Store",
    "ValidationError",
]


def __getattr__(name: str):
    """Lazy-load cloud storage classes to avoid heavy SDK imports."""
    if name == "AzureBlobEngine":
        from .storage_engines.azure_engine import AzureBlobEngine

        return AzureBlobEngine
    if name == "AzureStorage":
        from .azure import AzureStorage

        return AzureStorage
    if name == "GCSEngine":
        from .storage_engines.gcs_engine import GCSEngine

        return GCSEngine
    if name == "GCSStorage":
        from .gcs import GCSStorage

        return GCSStorage
    if name == "S3Engine":
        from .storage_engines.s3_engine import S3Engine

        return S3Engine
    if name == "S3Storage":
        from .s3 import S3Storage

        return S3Storage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
