"""
This module contains the LocalStorage class.
"""

from logging import getLogger

from .main import FastStore, FileData, FileField
from .storage_engines import LocalEngine


logger = getLogger()


class LocalStorage(FastStore):
    """Local storage for FastAPI.
    """
    StorageEngine = LocalEngine

    # noinspection PyTypeChecker
    async def upload(self, *, file_field: FileField):
        try:
            file_data = await self.engine.upload(file_field=file_field)
            self.store = file_data
        except Exception as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            self.store = FileData(status=False, error='Something went wrong', field_name=file_field['name'],
                                  message=f'Unable to upload {file_field["name"]}')