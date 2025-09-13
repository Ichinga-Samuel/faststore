"""
This module contains the LocalStorage class.
"""
import asyncio
from pathlib import Path
from logging import getLogger

from starlette.datastructures import UploadFile

from ..exceptions import FileStoreError
from ..datastructures import FileField, FileData
from .storage_engine import StorageEngine

logger = getLogger(__name__)


class LocalEngine(StorageEngine):
    """Local storage for FastAPI."""
    @staticmethod
    def get_path(filename: str, destination: str | Path = "") -> Path:
        """Get the path to save the file to.

        Returns:
            Path: The path to save the file to.
        """
        if isinstance(destination, Path) and destination.is_absolute():
            Path(destination).mkdir(parents=True, exist_ok=True)
        else:
            destination = Path.cwd() / destination
            Path(destination).mkdir(parents=True, exist_ok=True)
        return destination / filename

    async def _upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Private method to upload the file to the destination. This method is called by the upload method.

        Args:
            file_field (FileField): The file field to upload.
            file (UploadFile): The file to upload.

        Returns:
            FileData: The file upload result.
        """
        try:
            config = file_field.config
            dest = config.get('destination', "")
            dest = dest(self.request, self.form, file_field.name, file) if callable(dest) else self.get_path(file.filename, dest)
            print(dest, 'destination')
            file_object = await file.read()
            with open(f'{dest}', 'wb') as fh:
                fh.write(file_object)
            await file.close()
            message = f'{file.filename} was saved successfully for field {file_field.name}'
            return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                     path=dest, field_name=file_field.name, message=message, status=True)
        except Exception as err:
            logger.error(f'Error Saving file to Local: {err} in {self.__class__.__name__}')
            return FileData(field_name=file_field.name, filename=file.filename, error=str(err), status=False)

    async def upload(self, file_field: FileField) -> FileData | list[FileData]:
        """Upload a file to the destination.

        Args:
            file_field (FileField): A file field object.

        Returns:
            FileData | list[FileData]: The file upload result(s).
        """
        try:
            config = file_field.config
            files = self.form.getlist(file_field.name)
            print(file_field.name, files, file_field.max_count)
            if len(files) == 1:
                file = files[0]
                if config['background']:
                    self.background_tasks.add_task(self._upload, file_field, file)
                    message = f'{file.filename} is saving in the background'
                    return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                                    status=True, field_name=file_field.name, message=message)
                else:
                    return await self._upload(file_field, file)

            elif len(files) > 1:
                if config['background']:
                    for file in files:
                        self.background_tasks.add_task(self._upload, file_field, file)
                    message = f'{len(files)} are saving in the background for field {file_field.name}'
                    return FileData(status=True, field_name=file_field.name, message=message)
                results = await asyncio.gather(*[self._upload(file_field, file) for file in files], return_exceptions=True)
                file_data = []
                for res in results:
                    if isinstance(res, FileData):
                        file_data.append(res)
                    elif isinstance(res, Exception):
                        file_data.append(FileData(field_name=file_field.name, error=str(res), status=False))
                return file_data
            else:
                raise FileStoreError(f'No file found for field {file_field.name}')
        except Exception as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            raise FileStoreError(err)
