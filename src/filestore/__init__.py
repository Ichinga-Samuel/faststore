"""
import public modules and classes from faststore
"""
from .main import FastStore, FileData, Store, FileField
from .memorystorage import MemoryStorage
from .localstorage import LocalStorage
from .store import FileStore
from .exceptions import FileStoreError
from .structs import FileField, FileData, Config, UploadFile
from .storage_engines import StorageEngine, LocalEngine, MemoryEngine

try:
    from .s3 import S3Engine, S3Storage
except ImportError as err:
    pass