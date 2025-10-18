"""
This module contains a test FastAPI application and the endpoints.
"""
import base64
import random
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form
from fastapi.datastructures import FormData, UploadFile
from typing import Annotated

from filestore import FileData, Store, MemoryStorage, LocalStorage, FileField
from filestore.s3 import S3Storage
from filestore.util import FileModel

from dotenv import load_dotenv

load_dotenv()


def file_destination(req: Request, form: FormData, field: str, file: UploadFile) -> Path:
    """Get the title from the form and create a folder with the title as the folder name."""
    folder = form["title"]
    path = Path.cwd() / f"test_data/uploads/books/{folder}"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{file.filename}"


def s3_file_destination(req: Request, form: FormData, field: str, file: UploadFile) -> str:
    """Get the title from the form and create a folder with the title as the folder name."""
    title = form.get("title", "")
    return f"test_data/uploads/books/{file.filename}" if title else f"test_data/uploads/books/{title}/{file.filename}"


def image_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for the image files"""
    return file.filename.rsplit(".", 1)[1].lower() in ["jpg", "png", "jpeg"]


def size_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for the image files"""
    return file.size <= 1500000  # 1.5MB


def book_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    return file.filename.rsplit(".", 1)[1].lower() in ["txt", "pdf", "epub", "mobi"]


def cover_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """A filename function for the cover file"""
    title = form["title"]
    file.filename = f"{title}_cover_{random.randint(1, 10)}.{file.filename.rsplit('.', maxsplit=1)[1]}"
    return file


single_local = LocalStorage(name="book", config={"destination": "test_data/uploads/books", "filters": book_filter})
mul_fields = [
    FileField(name="book_files", max_count=3, config={"filters": book_filter}),
    FileField(name="authors_images", max_count=2, config={"filters": image_filter}),
    FileField(name="covers", max_count=2, config={"filename": cover_filename, "filters": image_filter}),
]
multiple_local = LocalStorage(fields=mul_fields, config={"destination": file_destination, "filters": size_filter, "background": True})
mem_store = MemoryStorage(name="book", count=2)
s3_store = S3Storage(name="title", config={"destination": s3_file_destination, "background": True})
app = FastAPI()


@app.post("/local_multiple")
async def local_multiple(title: Annotated[str, Form()], model = Depends(FileModel(multiple_local)),
                         files: Store = Depends(multiple_local)) -> Store:
    """Local storage multiple file upload endpoint.
    Args:
        title (Annotated[str, Form()]): The title of the file.
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        files (LocalStorage): The LocalStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    return files


# @app.post('/s3_multiple', name='s3_multiple', openapi_extra={'form': {'multiple': True}})
# async def s3_multiple(model=Depends(multiple_s3.model), s3=Depends(multiple_s3)) -> Store:
#     """
#     S3 storage multiple file upload endpoint.
#
#     Args:
#         model (FormModel): The form model dynamically built from the form file fields.
#             This only useful to swagger UI to show the form fields.
#         s3 (S3Storage): The S3Storage instance.
#
#     Returns:
#         Store: The result of the storage operation.
#     """
#     return s3.store


@app.post('/s3_single', name='s3_single')
async def s3_single(model=Depends(FileModel(s3_store)), s3=Depends(s3_store)) -> Store:
    return s3


@app.post("/single_memory", name='single_memory')
async def mem_single(model=Depends(FileModel(mem_store)), mem: Store = Depends(mem_store)):
    """Memory storage single file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        mem (MemoryStorage): The MemoryStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    return mem.status
