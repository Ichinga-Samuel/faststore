from pathlib import Path
from logging import getLogger
from dataclasses import dataclass, field
from typing import Type, Callable, TypedDict

from starlette.requests import Request, FormData
from starlette.datastructures import UploadFile

logger = getLogger(__name__)


class Config(TypedDict, total=False):
    """
    The configuration dict for both the Faststore and the FileField classes.
    """
    destination: Callable[[Request, FormData, str, UploadFile], str | Path] | str | Path
    filter: Callable[[Request, FormData, str, UploadFile], bool]
    max_files: int
    max_fields: int
    max_part_size: int
    filename: Callable[[Request, FormData, str, UploadFile], UploadFile]
    background: bool
    extra_args: dict
    bucket: str
    region: str
    storage_engine: 'StorageEngine'
    StorageEngine: Type['StorageEngine']


@dataclass
class FileField:
    """
    The fields of the FileField class.
    """
    name: str
    file: UploadFile | list[UploadFile] = None
    max_count: int = 1
    required: bool = False
    config: Config = field(default_factory=dict)


@dataclass
class FileData:
    """
    The Store of a file storage operation.

    Attributes:
        path (str): The path to the file for local storage.
        url (str): The url to the file for cloud storage.
        status (bool): The status of the file storage operation.
        content_type (str): The content type of the file.
        filename (str | bytes): The name of the file or the file object.
        size (int): The size of the file.
        file (bytes | None): The file object for memory storage.
        field_name (str): The name of the form field.
        metadata (dict): Extra metadata of the file.
        error (str): The error message if the file storage operation failed.
        message (str): Success message if the file storage operation was successful.
    """
    #Todo:
    # field_name should not be optional
    field_name: str = None
    path: str | Path = None
    url: str = None
    status: bool = False
    content_type: str = None
    filename: str = None
    size: int = None
    file: bytes  = None
    metadata: dict = None
    error: str = None
    message: str = None

@dataclass
class Store:
    """
    The response model for the FastStore class.

    Attributes:
        file (FileData | None): The Store of a single file upload or storage operation.
        files (Dict[str, List[FileData]]): The response of the file storage operations(s) as a dictionary of field name and
            FileData arranged by field name and filename
        error (str): The error message if the file storage operation failed.
        message (str): A general response message if the file storage operation was successful.
    """
    file: FileData = None
    files: dict[str, list[FileData]] = None
    error: str = None
    message: str = None
    status: bool = True
