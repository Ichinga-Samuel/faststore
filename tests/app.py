"""
This module contains a test FastAPI application and the endpoints.
"""
import base64

from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, Response
from typing import List
import uvicorn
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from base64 import b64encode
from filestore import FileData, Store
from .utils import single_local, multiple_local, single_mem, multiple_mem, single_s3, multiple_s3, filestore
load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory='.')


@app.get('/')
async def home(req: Request):
    """
    Home page. Renders the home.html template.
    """
    return templates.TemplateResponse('home.html', {'request': req, 'data': {}})


@app.post('/local_single')
async def local_single(model=Depends(single_local.model), loc=Depends(single_local)) -> Store:
    """Local storage single file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        loc (LocalStorage): The LocalStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    return loc.store


@app.post('/local_multiple', openapi_extra={'form': {'multiple': True}})
async def local_multiple(model=Depends(multiple_local.model), loc=Depends(multiple_local)) -> Store:
    """Local storage multiple file upload endpoint.
    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        loc (LocalStorage): The LocalStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    # print(type(loc))
    return loc.store


@app.post('/s3_multiple', name='s3_multiple', openapi_extra={'form': {'multiple': True}})
async def s3_multiple(model=Depends(multiple_s3.model), s3=Depends(multiple_s3)) -> Store:
    """
    S3 storage multiple file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        s3 (S3Storage): The S3Storage instance.

    Returns:
        Store: The result of the storage operation.
    """
    return s3.store


@app.post('/s3_single', name='s3_single')
async def s3_single(model=Depends(single_s3.model), s3=Depends(single_s3)) -> Store:
    return s3.store


@app.post('/single_memory', name='single_memory')
async def mem_single(model=Depends(single_mem.model), mem=Depends(single_mem)):
    """Memory storage single file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
        mem (MemoryStorage): The MemoryStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    # img = f"""data:image/png;base64, {b64encode(mem.store.file.file).decode('utf-8')}"""
    mem.store.file.file = b64encode(mem.store.file.file)
    return mem.store

@app.post('/multiple_memory', name='multiple_memory')
async def mem_multiple(model=Depends(multiple_mem.model), mem=Depends(multiple_mem)) -> Store:
    """
    Memory storage multiple file upload endpoint.

    Args:
        model (FormModel): The form model dynamically built from the form file fields.
            This only useful to swagger UI to show the form fields.
       mem (MemoryStorage): The MemoryStorage instance.

    Returns:
        Store: The result of the storage operation.
    """
    for field in mem.store.files:
        for filedata in mem.store.files[field]:
            filedata.file = b64encode(filedata.file)
    return mem.store


@app.post('/filestore', name='filestore')
async def filestore(model=Depends(filestore.model), files=Depends(filestore)) -> FileData | List[FileData]:
    return files


if __name__ == "__main__":
    uvicorn.run("app:app", port=5000, log_level="info")