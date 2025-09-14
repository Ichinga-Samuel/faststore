"""
This module contains a test FastAPI application and the endpoints.
"""
import base64
from pathlib import Path
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, Response
from fastapi.datastructures import FormData, UploadFile
from typing import Annotated
from filestore import FileData, Store, MemoryStorage, LocalStorage, FileField
from filestore.util import model
from pydantic import BaseModel, Field


def local_book_destination(req: Request, form: FormData, field: str, file: UploadFile) -> Path:
    """Get the title from the form and create a folder with the title as the folder name."""
    print(form, 'local book destination')
    folder = form.get('title', 'boll')
    path = Path.cwd() / f'test_files/uploads/books/{folder}'
    path.mkdir(parents=True, exist_ok=True) if not path.exists() else ...
    return path / f'{file.filename}'

def author_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """A filename function for the author file"""
    name = form['author_name']
    file.filename = f'{name}.{file.filename.rsplit(".", maxsplit=1)[1]}'
    return file

def image_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for the image files"""
    return file.filename.rsplit('.', 1)[1].lower() in ['jpg', 'png', 'jpeg']

def size_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    """A filter function for the image files"""
    return file.size <= 1500000  # 1.5MB

def book_filter(req: Request, form: FormData, field: str, file: UploadFile) -> bool:
    return file.filename.rsplit('.', 1)[1].lower() in ['txt', 'pdf', 'epub', 'docx', 'doc']

def cover_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """A filename function for the cover file"""
    title = form['title']
    file.filename = f'{title}_cover.{file.filename.rsplit(".", maxsplit=1)[1]}'
    return file


# single_mem = MemoryStorage(name='cover', required=True, config={'filter': image_filter})
#
# multiple_mem = MemoryStorage(fields=[{'name': 'covers', 'max_count': 2, 'config': {'filter': image_filter}},
#                                      {'name': 'book', 'config': {'filter': size_filter}}])

single_local = LocalStorage(name="book", config={"destination": "test_data/uploads/Books", "filter": book_filter})

mul_fields = [
    FileField(name="books", max_count=3, config={"filter": book_filter}),
    FileField(name="authors", max_count=2, config={"filename": author_filename}),
]

multiple_local = LocalStorage(fields=mul_fields, config={"destination": local_book_destination, "filter": image_filter})

class BookForm(BaseModel):
    title: str
    author_name: str

app = FastAPI()

# templates = Jinja2Templates(directory='.')


# @app.get('/')
# async def home(req: Request):
#     """
#     Home page. Renders the home.html template.
#     """
#     return templates.TemplateResponse('home.html', {'request': req, 'data': {}})

@app.post('/local_single')
async def local_single(model = Depends(model(single_local)), book = Depends(single_local)):
    """Local storage single file upload endpoint.
LocalStorage
    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        book (LocalStorage): The LocalStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    ...

@app.post("/local_multiple")
async def local_multiple(book: Annotated[BookForm, Form()],
                         files=Depends(multiple_local), models=Depends(model(multiple_local))):
    """Local storage multiple file upload endpoint.
    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        files (LocalStorage): The LocalStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    print(author_name)



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


# @app.post('/s3_single', name='s3_single')
# async def s3_single(model=Depends(single_s3.model), s3=Depends(single_s3)) -> Store:
#     return s3.store


# @app.post('/single_memory', name='single_memory')
# async def mem_single(model=Depends(single_mem.model), mem=Depends(single_mem)):
#     """Memory storage single file upload endpoint.
#
#     Args:
#         model (FormModel): The form model dynamically built from the form file fields.
#             This only useful to swagger UI to show the form fields.
#         mem (MemoryStorage): The MemoryStorage instance.
#
#     Returns:
#         Store: The result of the storage operation.
#     """
#     # img = f"""data:image/png;base64, {b64encode(mem.store.file.file).decode('utf-8')}"""
#     mem.store.file.file = b64encode(mem.store.file.file)
#     return mem.store

# @app.post('/multiple_memory', name='multiple_memory')
# async def mem_multiple(model=Depends(multiple_mem.model), mem=Depends(multiple_mem)) -> Store:
#     """
#     Memory storage multiple file upload endpoint.
#
#     Args:
#         model (FormModel): The form model dynamically built from the form file fields.
#             This only useful to swagger UI to show the form fields.
#        mem (MemoryStorage): The MemoryStorage instance.
#
#     Returns:
#         Store: The result of the storage operation.
#     """
#     for field in mem.store.files:
#         for filedata in mem.store.files[field]:
#             filedata.file = b64encode(filedata.file)
#     return mem.store


# @app.post('/filestore', name='filestore')
# async def filestore(model=Depends(filestore.model), files=Depends(filestore)) -> Union[FileData, List[FileData]]:
#     return files
