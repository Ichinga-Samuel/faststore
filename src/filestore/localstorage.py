"""Local filesystem storage shortcut."""

from .main import FileStore
from .storage_engines import LocalEngine


class LocalStorage(FileStore):
    """Pre-configured :class:`FileStore` using the local filesystem backend."""

    StorageEngine = LocalEngine
