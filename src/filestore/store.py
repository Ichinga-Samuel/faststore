"""
Single storage class to handle multiple storage option
"""
import asyncio
from typing import Type, List, Dict, Union
from random import randint
from logging import getLogger

from starlette.datastructures import FormData
from fastapi import Request, BackgroundTasks
from pydantic import create_model, Field, BaseModel as FormModel

# from .util import FormModel
from .structs import UploadFile, Config, FileField, cache, FileData
from .main import _file_filter, file_filter, filename

from .storage_engines import MemoryEngine, StorageEngine, LocalEngine
from .exceptions import FileStoreError

logger = getLogger()


class FileStore:
    fields: List[FileField]
    config: Config
    form: FormData
    request: Request
    background_tasks: BackgroundTasks
    file_count: int

    def __init__(self, name: str = '', count: int = 1, required=False, storage: Type[StorageEngine] = LocalEngine,
                 fields: List[FileField] = None, config: Config = None):
        field = {'name': name, 'max_count': count, 'required': required, 'storage': storage} if name else {}
        self.fields = fields or []
        self.fields.append(field) if field else ...
        self.config = {'max_files': 1000, 'max_fields': 1000, 'filename': filename, 'background': False,
                       **(config or {})}

    @property
    @cache
    def model(self) -> Type[FormModel]:
        """
        Returns a pydantic model for the form fields.
        Returns (FormModel):
        """
        body = {}
        for field in self.fields:
            if field.get('max_count', 1) > 1:
                body[field['name']] = (List[UploadFile], ...) if field.get('required', False) \
                    else (List[UploadFile], Field([], validate_default=False))
            else:
                body[field['name']] = (UploadFile, ...) if field.get('required', False) \
                    else (UploadFile, Field(None, validate_default=False))
        model_name = f"FormModel{randint(100, 1000)}"
        model = create_model(model_name, **body, __base__=FormModel)
        return model

    async def __call__(self, req: Request, bgt: BackgroundTasks) -> Union[FileData, List[FileData]]:
        self.request = req
        self.background_tasks = bgt
        try:
            max_files, max_fields = self.config['max_files'], self.config['max_fields']
            form = await req.form(max_files=max_files, max_fields=max_fields)
            self.form = form
            file_fields: List[Union[FileField, Dict]] = []
            for field in self.fields:
                name = field['name']
                count = field.get('max_count', None)
                files = form.getlist(name)[: count]
                field['config'] = {**self.config, **field.get('config', {})}
                for file in files:
                    config = field['config']
                    _filter = config.get('filter', file_filter)
                    if not (_file_filter(file) and _filter(req, form, name, file)): continue
                    file_dict = {**field, 'file': config.get('filename', filename)(req, form, name, file)}
                    file_fields.append(file_dict)

            if not file_fields:
                return FileData(status=False, error='No files uploaded', message='No files uploaded')

            elif len(file_fields) == 1:
                return await self.upload(file_field=file_fields[0])
            else:
                return await self.multi_upload(file_fields=file_fields)
        except Exception as err:
            logger.error(f'Error uploading files: {err} in {self.__class__.__name__}')
            raise FileStoreError(err)

    async def upload(self, *, file_field: FileField) -> FileData:
        """Upload a single file using the specified storage service.

        Args:
            file_field (FileField): A FileField dictionary instance.
        """
        try:
            storage_cls = file_field.get('storage', MemoryEngine)
            storage = storage_cls(request=self.request, form=self.form, background_tasks=self.background_tasks,
                                  file_field=file_field)
            return await storage.upload()
        except FileStoreError as err:
            logger.error(f'Error uploading file: {err} in {self.__class__.__name__}')
            return FileData(status=False, error='Something went wrong', field_name=file_field['name'],
                            message=f'Unable to upload {file_field["name"]}')

    async def multi_upload(self, *, file_fields: List[Union[FileField, Dict]]) -> List[FileData]:
        """Upload multiple files with there respective storage engine

        Args:
            file_fields (list[FileField]): A list of FileFields to upload.
        """
        return await asyncio.gather(*[self.upload(file_field=file_field) for file_field in file_fields])