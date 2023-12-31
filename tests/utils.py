"""
Utility functions for creating test cases.
"""
from pathlib import Path

from fastapi import Request, UploadFile
from starlette.datastructures import FormData

from filestore import LocalStorage, MemoryStorage, FileStore, S3Storage, LocalEngine, S3Engine


def local_book_destination(req: Request, form: FormData, field: str, file: UploadFile) -> Path:
    """Get the title from the form and create a folder with the title as the folder name."""
    folder = form['title']
    path = Path.cwd() / f'test_data/uploads/Books/{folder}'
    path.mkdir(parents=True, exist_ok=True) if not path.exists() else ...
    return path / f'{file.filename}'


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
    file.filename = f'{title}_Cover.{file.filename.rsplit(".", maxsplit=1)[1]}'
    return file


def author_filename(req: Request, form: FormData, field: str, file: UploadFile) -> UploadFile:
    """A filename function for the author file"""
    name = form['author_name']
    file.filename = f'{name}.{file.filename.rsplit(".", maxsplit=1)[1]}'
    return file


def s3_destination(req: Request, form: FormData, field: str, file: UploadFile) -> str:
    """S3 storage destination function."""
    name = form['title']
    return f'Books/{name}/{file.filename}'


# FastStore instances to be used in the app as dependencies.
multiple_s3 = S3Storage(fields=[{'name': 'book', 'max_count': 2, 'config': {'filter': book_filter}},
                                {'name': 'cover', 'config': {'filename': cover_filename}}, {'name': 'author',
                                'config': {'filename': author_filename}}],
                        config={'destination': s3_destination, 'filter': image_filter})

single_s3 = S3Storage(name='book', required=True, config={'filter': book_filter, 'destination': 'Books'})

single_mem = MemoryStorage(name='cover', required=True, config={'filter': image_filter})

multiple_mem = MemoryStorage(fields=[{'name': 'covers', 'max_count': 2, 'config': {'filter': image_filter}},
                                     {'name': 'book', 'config': {'filter': size_filter}}])

single_local = LocalStorage(name='book', config={'destination': 'test_data/uploads/Books', 'filter': book_filter})

multiple_local = LocalStorage(fields=[{'name': 'books', 'max_count': 2, 'config': {'filter': book_filter}},
                                      {'name': 'cover', 'config': {'filename': cover_filename}}, {'name': 'author',
                                      'config': {'filename': author_filename}}],
                              config={'destination': local_book_destination, 'filter': image_filter})

filestore = FileStore(fields=[{'name': 'books', 'max_count': 2, 'storage': LocalEngine,
                               'config': {'destination': 'test_data/uploads/Books', 'filter': book_filter}},
                              {'name': 'covers', 'max_count': 2, 'storage': S3Engine, 'config': {'destination': 'Covers',
                                                                                            'background': True,
                                                                                            'filter': image_filter}}])