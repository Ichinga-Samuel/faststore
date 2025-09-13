"""This module contains the main classes and methods for the filestore package."""
import asyncio
from typing import Type
from logging import getLogger

from starlette.datastructures import FormData
from starlette.background import BackgroundTasks
from starlette.requests import Request

from .datastructures import FileField, FileData, Store, Config
from .storage_engines import StorageEngine
from .exceptions import FileStoreError

logger = getLogger(__name__)


class FileStore:
    """
    The base class for the FastStore package. It is an abstract class and must be inherited from for custom file
    storage services. The upload and multi_upload methods must be implemented in a child class.

    Attributes:
        fields (list[FileField]): The fields to expect from the form.
        request (Request): The request object.
        form (FormData): The form data object.
        config (dict): The configuration for the storage service.
        engine (StorageEngine): The storage engine instance for the file storage service.
        StorageEngine (Type[StorageEngine]): The storage engine class for the file storage service.
        background_tasks (BackgroundTasks): The background tasks object for running tasks in the background.

    Methods:
        upload (Callable[[FileField]]): The method to upload a single file.

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
    fields: list[FileField]
    config: Config
    form: FormData
    request: Request
    background_tasks: BackgroundTasks
    engine: StorageEngine
    StorageEngine: Type[StorageEngine]

    def __init__(self, name: str = None, count: int = 1, required=False, fields: list[FileField] = None,
                 config: Config | dict = None):
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
        if fields is None:
            self.fields = [FileField(name=name, max_count=count, required=required)] if name else []
        else:
            self.fields = fields or []
        self.config = {'background': False, **(config or {})}

    def get_form_args(self) -> dict:
        return {"max_files": self.config.get("max_files", 1000), "max_fields": self.config.get("max_fields", 1000),
         "max_part_size": self.config.get("max_part_size", 1024 * 1024)}

    async def __call__(self, request: Request, background_tasks: BackgroundTasks) -> Store:
        """
        Upload files to a storage service. This enables the FastStore class instance to be used as a dependency.

        Args:
            request (Request): The request object.
            background_tasks (BackgroundTasks): The background tasks object for running tasks in the background.

        Returns:
            FastStore: An instance of the FastStore class.
        """
        self.request = request
        self.background_tasks = background_tasks
        try:
            self.form = await request.form(**self.get_form_args())
            self.engine = self.StorageEngine(request=request, form=self.form, background_tasks=background_tasks)
            self.config['storage_engine'] = self.engine
            for _field in self.fields:
                if Engine := _field.config.get('StorageEngine'):
                    _field.config['storage_engine'] = Engine(request=request, form=self.form, background_tasks=background_tasks)
                _field.config = {**self.config, **(_field.config or {})}

            if not self.fields:
                return Store(status=False, error='No files were uploaded')

            elif len(self.fields) == 1:
                res = await self.upload(file_field=self.fields[0])
                return self.set_store(res)
            else:
                print('multiple files were uploaded')
                res = await asyncio.gather(*[self.upload(file_field=_field) for _field in self.fields], return_exceptions=True)
                return self.set_store(res)
        except FileStoreError as err:
            print('in call', 'return store?')
            logger.error(f'Error uploading files: {err} in {self.__class__.__name__}')
            return Store(status=False, error="An error occurred while uploading files")

    @staticmethod
    def set_store(value: FileData | list[FileData]) -> Store:
        if isinstance(value, FileData):
            return Store(message=value.message, status=value.status, error=value.error, file=value)
        elif isinstance(value, list):
            store = Store(files={})
            for file in value:
                if isinstance(file, FileData):
                    store.files.setdefault(f'{file.field_name}', []).append(file)
            return store
        return Store(error='No files were uploaded', status=False)

    async def upload(self, *, file_field: FileField | list[FileField]) -> FileData | list[FileData]:
        """Upload a single file to a storage service.

        Args:
            file_field (FileField): A FileField dictionary instance.
        """
        ...

