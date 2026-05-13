"""Google Cloud Storage shortcut."""

from __future__ import annotations

from .main import FileStore


class GCSStorage(FileStore):
    """Pre-configured :class:`FileStore` using the Google Cloud Storage backend.

    The ``filestore[gcp]`` extra must be installed.
    """

    def __init__(self, *args, **kwargs):
        from .storage_engines.gcs_engine import GCSEngine

        self.StorageEngine = GCSEngine
        super().__init__(*args, **kwargs)
