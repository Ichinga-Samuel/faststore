from abc import abstractmethod, ABC

from starlette.requests import Request, FormData
from starlette.background import BackgroundTasks
from starlette.datastructures import UploadFile

from ..datastructures import FileData, FileField


class StorageEngine(ABC):
    def __init__(self, *, request: Request, form: FormData, background_tasks: BackgroundTasks):
        self.form = form
        self.request = request
        self.background_tasks = background_tasks

    @abstractmethod
    async def upload(self, file_field: FileField, file: UploadFile) -> FileData | list[FileData]:
        """"""
