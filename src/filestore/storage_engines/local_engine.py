"""
This module contains the LocalEngine class.
"""
from pathlib import Path
from logging import getLogger

from starlette.datastructures import UploadFile

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

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Private method to upload the file to the destination. This method is called by the upload method.

        Args:
            file_field (FileField): The file field to upload.
            file (UploadFile): The file to upload.

        Returns:
            FileData: The file upload result.
        """
        try:
            config = file_field.config
            dest = config.get("destination", "")
            dest = dest(self.request, self.form, file_field.name, file) if callable(dest) else self.get_path(file.filename, dest)
            file_object = await file.read()
            with open(f"{dest}", "wb") as fh:
                fh.write(file_object)
            await file.close()
            message = f"{file.filename} was saved successfully for field {file_field.name}"
            return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                     path=dest, field_name=file_field.name, message=message, status=True)
        except Exception as err:
            logger.error(f'Error Saving file to Local: {err} in {self.__class__.__name__}')
            return FileData(field_name=file_field.name, filename=file.filename, error=str(err), status=False)
