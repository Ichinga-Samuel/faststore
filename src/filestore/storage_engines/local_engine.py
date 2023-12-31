"""
This module contains the LocalStorage class.
"""
from pathlib import Path
from typing import Union
from logging import getLogger

from fastapi import UploadFile

from ..exceptions import FileStoreError
from ..structs import FileField, FileData
from .storage_engine import StorageEngine

logger = getLogger(__name__)


class LocalEngine(StorageEngine):
    """Local storage for FastAPI."""

    def get_path(self, file: UploadFile, destination: Union[str, Path]) -> Path:
        """Get the path to save the file to.

        Returns:
            Path: The path to save the file to.
        """
        if isinstance(destination, Path):
            Path(destination).mkdir(parents=True, exist_ok=True) if not destination.exists() else ...
        else:
            destination = Path.cwd() / destination
            Path(destination).mkdir(parents=True, exist_ok=True) if not destination.exists() else ...
        return destination / file.filename

    @staticmethod
    async def _upload(file: UploadFile, dest):
        """Private method to upload the file to the destination. This method is called by the upload method.

        Args:
            file (UploadFile): The file to upload.
            dest (Path): The destination to upload the file to.

        Returns:
            None: Nothing is returned.
        """
        file_object = await file.read()
        with open(f'{dest}', 'wb') as fh:
            fh.write(file_object)
        await file.close()

    async def upload(self, file_field=None) -> FileData:
        """Upload a file to the destination.

        Args:
            file_field (FileField): A file field object.

        Returns:
            None: Nothing is returned.
        """
        try:
            self.file_field = file_field
            field_name, file = self.file_field['name'], self.file_field['file']
            dest = self.config.get('destination', None)
            dest = dest(self.request, self.form, field_name, file) if callable(dest) else self.get_path(file, dest)
            if self.config['background']:
                self.background_tasks.add_task(self._upload, file, dest)
                message = f'{file.filename} is saving in the background'
            else:
                await self._upload(file, dest)
                message = f'{file.filename} was saved successfully'
            return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                            path=str(dest), field_name=field_name, message=message)
        except Exception as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            raise FileStoreError(err)