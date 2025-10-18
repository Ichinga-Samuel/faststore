"""
This module contains the LocalStorage class.
"""
from logging import getLogger

from .main import FileStore
from .storage_engines import LocalEngine

logger = getLogger()


class LocalStorage(FileStore):
    """Local storage class."""
    StorageEngine = LocalEngine