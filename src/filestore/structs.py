"""Data Structures"""

from typing import Any, Type, cast, TypeVar, Callable, Union, List, Dict
from pathlib import Path
from logging import getLogger
from collections import defaultdict

from starlette.datastructures import UploadFile as StarletteUploadFile, FormData
from fastapi import Request, UploadFile as UF, Form
from pydantic import BaseModel

try:
    td = True
    from typing import TypedDict
except ImportError:
    td = False
    Config = TypeVar('Config', bound=dict)
    FileField = TypeVar('FileField', bound=dict)

try:
    from functools import cache
except ImportError as err:
    from functools import lru_cache

    cache = lru_cache(maxsize=None)

logger = getLogger(__name__)
NoneType = type(None)
StorageEngine = TypeVar('StorageEngine', bound='StorageEngine')


class UploadFile(UF):
    @classmethod
    def validate(cls: Type["UploadFile"], v: Any) -> Any:
        if not isinstance(v, (StarletteUploadFile, str, type(None))):
            raise ValueError(f"Expected UploadFile, received: {type(v)}")
        return v

    @classmethod
    def _validate(cls, __input_value: Any, _: Any) -> "UploadFile":
        if not isinstance(__input_value, (StarletteUploadFile, str, type(None))):
            raise ValueError(f"Expected UploadFile, received: {type(__input_value)}")
        return cast(UploadFile, __input_value)


if td:
    class Config(TypedDict, total=False):
        """
        The configuration for the FastStore class.
        """
        destination: Union[Callable[[Request, Form, str, UploadFile], Union[str, Path]], str, Path]
        filter: Callable[[Request, Form, str, UploadFile], bool]
        max_files: int
        max_fields: int
        filename: Callable[[Request, Form, str, UploadFile], UploadFile]
        background: bool
        extra_args: dict
        bucket: str
        region: str
        storage: StorageEngine


    class FileField(TypedDict, total=False):
        """
        The fields of the FileField class.
        """
        name: str
        max_count: int
        required: bool
        file: UploadFile
        config: Config
        storage: StorageEngine


Self = TypeVar('Self', bound='FastStore')


class FileData(BaseModel):
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
    path: str = ''
    url: str = ''
    status: bool = True
    content_type: str = ''
    filename: str = ''
    size: int = 0
    file: Union[bytes, str] = None
    field_name: str = ''
    metadata: dict = {}
    error: str = ''
    message: str = ''


class Store(BaseModel):
    """
    The response model for the FastStore class.

    Attributes:
        file (FileData | None): The Store of a single file upload or storage operation.
        files (Dict[str, List[FileData]]): The response of the file storage operations(s) as a dictionary of field name and
            FileData arranged by field name and filename
        failed (Dict[str, List[FileData]]): The result of a failed file upload or storage operation as a dictionary of
            FileData arranged by field name and filename.
        error (str): The error message if the file storage operation failed.
        message (str): Success message if the file storage operation was successful.
    """
    file: Union[FileData, NoneType] = None
    files: Dict[str, List[FileData]] = defaultdict(list)
    failed: Dict[str, List[FileData]] = defaultdict(list)
    error: str = ''
    message: str = ''
    status: bool = True

    def __len__(self) -> int:
        total = 0
        for field in self.files.values():
            total += len(field)
        return total