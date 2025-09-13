"""
This module contains the LocalStorage class.
"""
from logging import getLogger

from .main import FileStore, FileData, FileField
from .storage_engines import LocalEngine


logger = getLogger()


class LocalStorage(FileStore):
    """Local storage class."""
    StorageEngine = LocalEngine

    async def upload(self, *, file_field: FileField) -> FileData | list[FileData]:
        try:
            engine = file_field.config.get('storage_engine', self.engine)
            return await engine.upload(file_field=file_field)
        except Exception as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            return FileData(status=False)
            # return FileData(status=False, error='Something went wrong', field_name=file_field.name,
            #                       message=f'Unable to upload {file_field.name}')