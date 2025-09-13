from typing import Type
from dataclasses import dataclass, field, make_dataclass
from functools import cache
from random import randint

from .main import FileStore

try:
    from fastapi import UploadFile
    from pydantic import BaseModel, create_model, Field
except ImportError:
    raise ImportError('Please install fastapi using pip install fastapi')


@cache
def model(obj: FileStore, name: str = "") -> Type[BaseModel]:
    """Returns a dataclass of the form fields

    Returns:
        Type[BaseModel]
    """
    body = {}
    for _field in obj.fields:
        if _field.max_count > 1:
            body[_field.name] = (list[UploadFile], ...) if _field.required \
                else (list[UploadFile], [])
        else:
            body[_field.name] = (UploadFile, ...) if _field.required \
                else (UploadFile, None)
    model_name = name or f"FormModel{randint(100, 1000)}"
    return create_model(model_name, **body, __base__=BaseModel)


# @cache
# def model(obj: FileStore, name: str = "") -> Type[dataclass]:
#     """Returns a dataclass of the form fields
#
#     Returns:
#         Type[dataclass]
#     """
#     body = []
#     for _field in obj.fields:
#         if _field.max_count > 1:
#             body.append((_field.name, list[UploadFile])) if _field.required \
#                 else body.append((_field.name, list[UploadFile], field(default_factory=list)))
#         else:
#             body.append((_field.name, UploadFile)) if _field.required \
#                 else body.append((_field.name, UploadFile, field(default=None)))
#     model_name = name or f"FormModel{randint(100, 1000)}"
#     return make_dataclass(model_name, body)