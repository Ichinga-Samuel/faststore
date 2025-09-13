"""
Memory storage for FastStore. This storage is used to store files in memory.
"""
import asyncio
from logging import getLogger
from fastapi import UploadFile

from .storage_engine import StorageEngine
from ..datastructures import FileField, FileData
from ..exceptions import FileStoreError

logger = getLogger()


class MemoryEngine(StorageEngine):
    """Memory storage Engine. This storage is used to store files in memory and returned as bytes."""
    async def _upload(self, file_field: FileField, file: UploadFile) -> FileData:
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
                            message=f'{file.filename} saved successfully', status=True)
        except Exception as err:
            logger.error(f'Error Saving file to Memory: {err} in {self.__class__.__name__}')
            return FileData(field_name=file_field.name, filename=file.filename, error=str(err), status=False)

    async def upload(self, file_field: FileField) -> FileData | list[FileData]:
        try:
            files = self.form.getlist(file_field.name)[: file_field.max_count]
            if len(files) == 1:
                file = files[0]
                return await self._upload(file_field=file_field, file=file)

            elif len(files) > 1:
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