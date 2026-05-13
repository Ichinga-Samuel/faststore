"""Azure Blob Storage shortcut."""

from __future__ import annotations

from .main import FileStore


class AzureStorage(FileStore):
    """Pre-configured :class:`FileStore` using the Azure Blob Storage backend.

    The ``filestore[azure]`` extra must be installed.
    """

    def __init__(self, *args, **kwargs):
        from .storage_engines.azure_engine import AzureBlobEngine

        self.StorageEngine = AzureBlobEngine
        super().__init__(*args, **kwargs)
