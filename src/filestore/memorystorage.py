"""
Memory storage class. This storage stores files in memory.
"""
from logging import getLogger

from .main import FileStore
from .storage_engines import MemoryEngine

logger = getLogger()


class MemoryStorage(FileStore):
    """Memory storage class"""
    StorageEngine = MemoryEngine
