"""
Memory storage for FastStore. This storage is used to store files in memory.
"""
from logging import getLogger

from fastapi import UploadFile

from .storage_engine import StorageEngine
from ..structs import FileField, FileData
from ..exceptions import FileStoreError

logger = getLogger()


class MemoryEngine(StorageEngine):
    """Memory storage Engine. This storage is used to store files in memory and returned as bytes."""

    async def upload(self, file_field: FileField = None) -> FileData:
        try:
            self.file_field = file_field
            file = self.file_field['file']
            obj = await file.read()
            await file.close()
            return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                            field_name=file_field['name'], file=obj,
                            message=f'{file.filename} saved successfully')
        except Exception as err:
            logger.error(f'Error Saving file to Memory: {err} in {self.__class__.__name__}')
            raise FileStoreError(err)