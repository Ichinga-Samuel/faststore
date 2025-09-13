"""
Memory storage class. This storage stores files in memory.
"""
from logging import getLogger

from .main import FileStore, FileData, FileField
from .storage_engines import MemoryEngine
from .exceptions import FileStoreError

logger = getLogger()


class MemoryStorage(FileStore):
    """Memory storage class"""
    StorageEngine = MemoryEngine

    async def upload(self, *, file_field: FileField) -> FileData | list[FileData]:
        try:
            return await self.engine.upload(file_field=file_field)
        except FileStoreError as err:
            logger.error(f'Error Saving file to Memory: {err} in {self.__class__.__name__}')
            return FileData(status=False, error="Something went wrong", field_name=file_field.name,
                                  message=f"Unable to upload {file_field.name}")