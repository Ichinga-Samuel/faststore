"""
Memory storage for FastStore. This storage is used to store files in memory.
"""
from logging import getLogger
from fastapi import UploadFile

from .storage_engine import StorageEngine
from ..datastructures import FileField, FileData

logger = getLogger()


class MemoryEngine(StorageEngine):
    """Memory storage Engine. This storage is used to store files in memory and returned as bytes."""
    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Private method to upload the file to memory. This method is called by the upload method.

        Args:
            file_field (FileField): A file field object.
            file (UploadFile): The file to upload.

        Returns:
            FileData: The Store of the file upload operation.
        """
        try:
            obj = await file.read()
            await file.close()
            return FileData(size=file.size, filename=file.filename, content_type=file.content_type,
                            field_name=file_field.name, file=obj,
                            message=f"{file.filename} saved successfully", status=True)
        except Exception as err:
            logger.error("%s: Error Saving file to memory in %s", err, self.__class__.__name__)
            return FileData(field_name=file_field.name, filename=file.filename, error=str(err), status=False)
