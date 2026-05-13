"""Storage engine subpackage.

Core engines (local, memory) are imported eagerly.  Cloud engines
(S3, GCS, Azure) are loaded lazily to avoid requiring their heavy
SDK dependencies at import time.
"""

from __future__ import annotations

from .local_engine import LocalEngine
from .memory_engine import MemoryEngine
from .storage_engine import StorageEngine

__all__ = ["StorageEngine", "LocalEngine", "MemoryEngine", "AzureBlobEngine", "GCSEngine", "S3Engine"]


def __getattr__(name: str):
    if name == "AzureBlobEngine":
        from .azure_engine import AzureBlobEngine

        return AzureBlobEngine
    if name == "GCSEngine":
        from .gcs_engine import GCSEngine

        return GCSEngine
    if name == "S3Engine":
        from .s3_engine import S3Engine

        return S3Engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
