"""This module contains the main class of the filestore package."""
import asyncio
from typing import Type
from logging import getLogger

from starlette.datastructures import FormData, UploadFile
from starlette.background import BackgroundTasks
from starlette.requests import Request

from .datastructures import FileField, FileData, Store, Config
from .storage_engines import StorageEngine, LocalEngine
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
    store: Store
    engine: StorageEngine
    StorageEngine: Type[StorageEngine] = LocalEngine

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
        self.config = {"background": False, **(config or {})}

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
            self.StorageEngine = self.config.get("StorageEngine", LocalEngine)
            self.engine = self.StorageEngine(request=request, form=self.form, background_tasks=background_tasks)
            for _field in self.fields:
                if Engine := _field.config.get("StorageEngine"):
                    _field.config["storage_engine"] = Engine(request=request, form=self.form, background_tasks=background_tasks)
                filters = _field.config.get("filters", [])
                filters = [filters] if not isinstance(filters, list) else filters
                c_filters = self.config.get("filters", [])
                c_filters = [c_filters] if not isinstance(c_filters, list) else c_filters
                filters.extend(c_filters)
                _field.config["filters"] = filters
                _field.config = {**self.config, **(_field.config or {})}

            if not self.fields:
                msg = "No files were uploaded"
                return Store(status=False, error=msg, message=msg)

            elif len(self.fields) == 1:
                res = await self.handle(file_field=self.fields[0])
                return self.set_store(res)
            else:
                res = await asyncio.gather(*[self.handle(file_field=_field) for _field in self.fields],
                                           return_exceptions=True)
                return self.set_store(res)
        except FileStoreError as err:
            logger.error("%s: Error uploading files %s in %s", err,)
            return Store(status=False, error="An error occurred while uploading files")

    @staticmethod
    def set_store(value: FileData | list[FileData | list[FileData]]) -> Store:
        store = Store(files={})
        if isinstance(value, FileData):
            store.files.setdefault(f"{value.field_name}", []).append(value)
            store.error = value.error
            store.message = value.message
            store.status = value.status
            return store
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, FileData):
                    store.files.setdefault(f"{item.field_name}", []).append(item)
                elif isinstance(item, list):
                    for n_item in item:
                        if isinstance(n_item, FileData):
                            store.files.setdefault(f"{n_item.field_name}", []).append(n_item)
            return store
        return Store(error="No files were uploaded", status=False)

    async def handle(self, *, file_field: FileField | list[FileField]) -> FileData | list[FileData]:
        """Upload a single file to a storage service.

        Args:
            file_field (FileField): A FileField dictionary instance.
        """
        try:
            config = file_field.config
            files = self.form.getlist(file_field.name)
            if filters := config.get("filters", []):
                files = [file for file in files if all(_filter(self.request, self.form, file_field.name, file) for _filter in filters)]
            files = files[: file_field.max_count]
            if callable(filename := config.get("filename")):
                files = [filename(self.request, self.form, file_field.name, file) for file in files ]
            if len(files) == 1:
                file = files[0]
                if config["background"]:
                    self.background_tasks.add_task(self.upload, file_field, file)
                    message = f"{file.filename} is uploading in the background"
                    return FileData(filename=file.filename, content_type=file.content_type,
                                    status=True, field_name=file_field.name, message=message)
                else:
                    # if file_field.name == 'covers':
                    #     print(files, file, 'handle')
                    return await self.upload(file_field, file)

            elif len(files) > 1:
                if config['background']:
                    for file in files:
                        self.background_tasks.add_task(self.upload, file_field, file)
                    message = f'{len(files)} are saving in the background for field {file_field.name}'
                    return FileData(status=True, field_name=file_field.name, message=message)
                results = await asyncio.gather(*[self.upload(file_field, file) for file in files], return_exceptions=True)
                file_data = []
                for res in results:
                    if isinstance(res, FileData):
                        file_data.append(res)
                    elif isinstance(res, Exception):
                        file_data.append(FileData(field_name=file_field.name, error=str(res), status=False))
                return file_data
            else:
                return FileData(status=False, field_name=file_field.name, message="No files were uploaded")
        except Exception as err:
            logger.error("%s: Error uploading file for %s in %s", err, file_field.name, self.__class__.__name__)
            raise FileStoreError(err)

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        """Upload a single file to a storage service."""
        try:
            engine = file_field.config.get("storage_engine", self.engine)
            return await engine.upload(file_field, file)
        except Exception as err:
            logger.error(f"Error uploading file: {err} in {self.__class__.__name__}")
            return FileData(status=False, error="Something went wrong", field_name=file_field.name,
                            message=f"Unable to upload {file_field.name}")
