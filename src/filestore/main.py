"""This module contains the main classes and methods for the filestore package."""

import asyncio
from typing import Type, TypeVar, List, Dict, Union
from abc import abstractmethod
from logging import getLogger
from random import randint

from starlette.datastructures import UploadFile as StarletteUploadFile, FormData
from fastapi import Request, BackgroundTasks
from pydantic import create_model, Field, BaseModel as FormModel

# from .util import FormModel
from .structs import FileField, FileData, Store, Config, cache, UploadFile
from .storage_engines import StorageEngine
from .exceptions import FileStoreError

logger = getLogger(__name__)
Self = TypeVar('Self', bound='FastStore')


def _file_filter(file):
    return isinstance(file, StarletteUploadFile) and file.filename


def file_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """
    The default config filter function for the FastStore class. This filter applies to all fields.

    Args:
        req (Request): The request object.
        form (FormData): The form data object.
        field (Field): The name of the field.
        file (UploadFile): The file object.

    Returns (bool): True if the file is valid, False otherwise.
    """
    return True


def filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """
    Update the filename of the file object.

    Args:
        req (Request): The request object.
        form (FormData): The form data object.
        field (Field): The name of the field.
        file (UploadFile): The file object.

    Returns (UploadFile): The file object with the updated filename.
    """
    return file


class FastStore:
    """
    The base class for the FastStore package. It is an abstract class and must be inherited from for custom file
    storage services. The upload and multi_upload methods must be implemented in a child class.

    Attributes:
        fields (list[FileField]): The fields to expect from the form.
        request (Request): The request object.
        form (FormData): The form data object.
        config (dict): The configuration for the storage service.
        _store (Store): The Store of the file storage operation.
        store (Store): Property to access and set the result of the file storage operation.
        file_count (int): The Total number of files in the request.
        engine (StorageEngine): The storage engine instance for the file storage service.
        StorageEngine (Type[StorageEngine]): The storage engine class for the file storage service.
        background_tasks (BackgroundTasks): The background tasks object for running tasks in the background.

    Methods:
        upload (Callable[[FileField]]): The method to upload a single file.

        multi_upload (Callable[List[FileField]]): The method to upload multiple files.

    Config:
        max_files (int): The maximum number of files to accept in a single request. Defaults to 1000.

        max_fields (int): The maximum number of fields to accept in a single request. Defaults to 1000.

        filename (Callable[[Request, FormData, str, UploadFile], UploadFile): A function that takes in the request,
            form and file, filename modifies the filename attribute of the file and returns the file.

        destination (Callable[[Request, FormData, str, UploadFile], str | Path]): A string a path or a function that
            takes in the request, form and file and returns a path to save the file to in the storage service.

        filter (Callable[[Request, FormData, str, UploadFile], bool]): A function that takes in the request,
            form and file and returns a boolean.

        background (bool): A boolean to indicate if the file storage operation should be run in the background.

        extra_args (dict): Extra arguments to pass to the storage service.

        bucket (str): The name of the bucket to upload the file to in the cloud storage service.
    """
    fields: List[FileField]
    config: Config
    form: FormData
    request: Request
    background_tasks: BackgroundTasks
    file_count: int
    _store: Store
    store: Store
    engine: StorageEngine
    StorageEngine: Type[StorageEngine]

    def __init__(self, name: str = '', count: int = 1, required=False, fields: List[FileField] = None,
                 config: Config = None):
        """
        Initialize the FastStore class. For single file upload, specify the name of the file field and the expected
        number of files. If the field is required, set required to True.
        For multiple file uploads, specify the fields to expect from the form and the expected number
        of files for each field. If the field is required, set required to True.
        Use the config parameter to specify the configuration for the storage service.

        Keyword Args:
            name (str): The name of the file field to expect from the form for a single field upload.
            count (int): The maximum number of files to accept for single field upload.
            required (bool): required for single field upload. Defaults to false.
            fields: The fields to expect from the form. Usually for multiple file uploads from different fields.

        Note:
            If fields and name are specified then the name field is added to the fields list.
        """
        field = {'name': name, 'max_count': count, 'required': required} if name else {}
        self.fields = fields or []
        self.fields.append(field) if field else ...
        self.config = {'filter': file_filter, 'max_files': 1000, 'max_fields': 1000, 'filename': filename,
                       'background': False, **(config or {})}

    @property
    @cache
    def model(self) -> Type[FormModel]:
        """
        Returns a pydantic model for the form fields.

        Returns:
            FormModel
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

    async def __call__(self, req: Request, bgt: BackgroundTasks) -> Self:
        """
        Upload files to a storage service. This enables the FastStore class instance to be used as a dependency.

        Args:
            req (Request): The request object.
            bgt (BackgroundTasks): The background tasks object for running tasks in the background.

        Returns:
            FastStore: An instance of the FastStore class.
        """
        self._store = Store()
        self.request = req
        self.background_tasks = bgt
        try:
            max_files, max_fields = self.config['max_files'], self.config['max_fields']
            form = await req.form(max_files=max_files, max_fields=max_fields)
            self.form = form
            self.engine = self.StorageEngine(request=req, form=form, background_tasks=bgt)
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

            self.file_count = len(file_fields)
            if not file_fields:
                self._store = Store(message='No files were uploaded')
                return self

            elif len(file_fields) == 1:
                await self.upload(file_field=file_fields[0])

            else:
                await self.multi_upload(file_fields=file_fields)
        except FileStoreError as err:
            logger.error(f'Error uploading files: {err} in {self.__class__.__name__}')
            self._store = Store(error=str(err), status=False)
        return self

    @abstractmethod
    async def upload(self, *, file_field: FileField):
        """Upload a single file to a storage service.

        Args:
            file_field (FileField): A FileField dictionary instance.
        """
    async def multi_upload(self, *, file_fields: List[FileField]):
        """
        Upload multiple files to a storage service.

        Args:
            file_fields (list[FileField]): A list of FileFields to upload.
        """
        await asyncio.gather(*[self.upload(file_field=file_field) for file_field in file_fields])

    @property
    def store(self) -> Store:
        """
        Returns the Store of the file storage.

        Returns:
            Store: The Store of the file storage operation.
        """
        success = sum(len(files) for files in self._store.files.values())
        failed = sum(len(files) for files in self._store.failed.values())
        self._store.message = f'{success} files uploaded successfully' if success else ''
        self._store.error = f'{failed} file(s) not uploaded' if failed else ''
        return self._store

    @store.setter
    def store(self, value: FileData):
        """
        Sets the Store of the file storage operation.

        Args:
            value: A FileData instance.
        """
        try:
            if not isinstance(value, FileData):
                logger.error(f'Expected FileData instance, got {type(value)} in {self.__class__.__name__}')
                return
            if self.file_count == 1:
                if value.status:
                    self._store.file = value
                    self._store.files[f'{value.field_name}'].append(value)
                else:
                    self._store.failed[f'{value.field_name}'].append(value)
            else:
                if value.status:
                    self._store.files[f'{value.field_name}'].append(value)
                else:
                    self._store.failed[f'{value.field_name}'].append(value)
        except Exception as err:
            logger.error(f'Error setting Store in {self.__class__.__name__}: {err}')