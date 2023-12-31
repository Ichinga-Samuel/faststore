import asyncio
from abc import abstractmethod, ABC

from fastapi import BackgroundTasks, Request

from ..structs import FileField, Config, FormData, List, UploadFile, FileData


class StorageEngine(ABC):

    def __init__(self, *, request: Request, form: FormData, background_tasks: BackgroundTasks,
                 file_field: FileField = None):
        self.form = form
        self.request = request
        self.background_tasks = background_tasks
        self._file_field = file_field or {}

    @property
    def config(self) -> Config:
        return self.file_field.get('config', {})

    @property
    def file_field(self):
        return self._file_field

    @file_field.setter
    def file_field(self, file_field: dict):
        file_field = file_field or {}
        self._file_field = file_field.copy() or self.file_field

    @abstractmethod
    async def upload(self, *, file_field) -> FileData:
        """"""

    async def multi_upload(self, *, file_fields: List[FileField]) -> List[FileData]:
        """"""
        return await asyncio.gather(*[self.upload(file_field=file_field) for file_field in file_fields])