from .main import FileStore, FileData, Store, FileField
from .memorystorage import MemoryStorage
from .localstorage import LocalStorage
from .exceptions import FileStoreError
from .datastructures import FileField, FileData, Config
from .storage_engines import StorageEngine, LocalEngine, MemoryEngine

# try:
#     from .s3 import S3Engine, S3Storage
# except ImportError as err:
#     pass