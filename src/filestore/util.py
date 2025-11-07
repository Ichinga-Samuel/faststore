from typing import Type
from functools import cache
from random import randint

from .main import FileStore

from fastapi import UploadFile
from pydantic import BaseModel, create_model


@cache
def FileModel(obj: FileStore, name: str = "") -> Type[BaseModel]:
    """Returns a dataclass of the form fields

    Returns:
        Type[BaseModel]
    """
    body = {}
    for _field in obj.fields:
        if _field.max_count > 1:
            body[_field.name] = list[UploadFile] if _field.required \
                else (list[UploadFile], list())
        else:
            body[_field.name] = UploadFile if _field.required \
                else (UploadFile, list())
    model_name = name or f"FormModel{randint(100, 1000)}"
    return create_model(model_name, **body, __base__=BaseModel)
