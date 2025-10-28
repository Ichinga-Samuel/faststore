"""
This module contains a test FastAPI application with endpoints that tests the various storage engines.
"""
import random
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Request, Depends, Form
from fastapi.datastructures import FormData, UploadFile

from filestore import Store, MemoryStorage, LocalStorage, FileField, FileStore, LocalEngine
from filestore.s3 import S3Storage, S3Engine
from filestore.util import FileModel

from dotenv import load_dotenv

load_dotenv()
app = FastAPI()


def local_file_destination(req: Request, form: FormData, field: str, file: UploadFile) -> Path:
    """Create a local file destination, using the title as folder name"""
    folder = form["title"]
    path = Path.cwd() / f"test_results/uploads/books/{folder}"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{file.filename}"


def s3_file_destination(req: Request, form: FormData, field: str, file: UploadFile) -> str:
    """Create a folder like structure in the s3 bucket, using the title as the folder name."""
    return f"test_results/uploads/books/{form["title"]}/{file.filename}"


def image_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for image files. Only jpg, png, and jpeg are supported."""
    return file.filename.rsplit(".", 1)[1].lower() in ["jpg", "png", "jpeg"]


def size_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for the image files."""
    return file.size <= 1500000  # 1.5MB


def book_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for accepted book file formats."""
    return file.filename.rsplit(".", 1)[1].lower() in ["pdf", "epub", "mobi"]


def cover_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """A filename function that renames the cover image with the title of the book."""
    title = form["title"]
    file.filename = f"{title}_cover {file.filename}"
    # file.filename = f"{title}_cover_{random.randint(1, 10)}.{file.filename.rsplit('.', maxsplit=1)[1]}"
    return file


# saves a single book file with local storage, destination is specified as a path.
single_local = LocalStorage(name="book", config={"destination": "test_results/uploads/books", "filters": book_filter})

# a list of file fields for saving books, authors, and cover-images.
local_fields = [
    FileField(name="book_files", max_count=3, config={"filters": book_filter}),
    FileField(name="authors_images", max_count=2, config={"filters": image_filter}),
    FileField(name="covers", max_count=2, config={"filename": cover_filename, "filters": image_filter}),
]

# local storage dependency that saves multiple files
# destination for all files are specified in the destination local_file_destination function
# a size_filter function to remove files larger than the size limit
local_store = LocalStorage(fields=local_fields, config={"destination": local_file_destination, "filters": size_filter})

# a memory storage dependency that saves two book files to memory
mem_store = MemoryStorage(name="book", count=2)

# s3 storage dependency with destination and size_filter functions
s3_fields = [
    FileField(name="book_files", max_count=3, config={"filters": book_filter}),
    FileField(name="authors_images", max_count=2, config={"filters": image_filter}),
    FileField(name="covers", max_count=2, config={"filename": cover_filename, "filters": image_filter}),
]
s3_store = S3Storage(fields=s3_fields, config={"destination": s3_file_destination, "filters": size_filter})

# a list of file fields for saving books, authors, and cover-images. Custom storage engines are specified in some of
# the configs
fields_2 = [
    FileField(name="book_files", max_count=3, config={"filters": book_filter, "StorageEngine": S3Engine,
                                                      "destination": s3_file_destination}),
    FileField(name="authors_images", max_count=2, config={"filters": image_filter}),
    FileField(name="covers", max_count=2, config={"filename": cover_filename, "filters": image_filter}),
]

# a multi-store dependency that can save to local storage, and S3 as the case maybe
multi_store = FileStore(fields=fields_2, config={"destination": local_file_destination,
                                                 "StorageEngine": LocalEngine, "filters": size_filter})

@app.post("/single_local/", name="single_local")
async def single_local(file: Store = Depends(single_local), model = Depends(FileModel(single_local))):
    """Local storage single file endpoint"""
    return file


@app.post("/local_store", name="local_store")
async def local_store(title: Annotated[str, Form()], model = Depends(FileModel(local_store)),
                      files: Store = Depends(local_store)) -> Store:
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


@app.post("/s3_store", name="s3_store")
async def s3_store(title: Annotated[str, Form()], model=Depends(FileModel(s3_store)), s3=Depends(s3_store)) -> Store:
    return s3


@app.post("/mem_store", name="mem_store")
async def mem_store(model=Depends(FileModel(mem_store)), mem: Store = Depends(mem_store)):
    """Memory storage single file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        mem (MemoryStorage): The MemoryStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    return mem.status


@app.post("/multi_store", name="multi_store")
async def multi_store(title: Annotated[str, Form()], model = Depends(FileModel(multi_store)),
                      files: Store = Depends(multi_store)) -> Store:
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
