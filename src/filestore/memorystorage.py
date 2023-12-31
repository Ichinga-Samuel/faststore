"""
Memory storage for FastStore. This storage is used to store files in memory.
"""
from logging import getLogger

from .main import FastStore, FileData, FileField
from .storage_engines import MemoryEngine
from .exceptions import FileStoreError

logger = getLogger()


class MemoryStorage(FastStore):
    """Memory storage for FastAPI. This storage is used to store files in memory and returned as bytes."""
    StorageEngine = MemoryEngine

    # noinspection PyTypeChecker
    async def upload(self, *, file_field: FileField):
        try:
            file_data = await self.engine.upload(file_field=file_field)
            self.store = file_data
        except FileStoreError as err:
            logger.error(f'Error Saving file to Memory: {err} in {self.__class__.__name__}')
            self.store = FileData(status=False, error='Something went wrong', field_name=file_field['name'],
                                  message=f'Unable to upload {file_field["name"]}')