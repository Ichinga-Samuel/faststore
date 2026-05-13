"""Amazon S3 storage shortcut."""

from __future__ import annotations

from .main import FileStore


class S3Storage(FileStore):
    """Pre-configured :class:`FileStore` using the Amazon S3 backend.

    The ``filestore[s3]`` extra must be installed.
    """

    def __init__(self, *args, **kwargs):
        from .storage_engines.s3_engine import S3Engine

        self.StorageEngine = S3Engine
        super().__init__(*args, **kwargs)
