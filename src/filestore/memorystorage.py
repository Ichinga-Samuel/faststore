"""In-memory storage shortcut."""

from .main import FileStore
from .storage_engines import MemoryEngine


class MemoryStorage(FileStore):
    """Pre-configured :class:`FileStore` using the in-memory backend."""

    StorageEngine = MemoryEngine
