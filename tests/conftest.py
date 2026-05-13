"""Shared test fixtures for the filestore test suite."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.requests import Request


def make_upload_file(
    content: bytes = b"hello world",
    filename: str = "test.txt",
    content_type: str = "text/plain",
) -> UploadFile:
    """Create an ``UploadFile`` backed by an in-memory buffer."""
    file = UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        size=len(content),
        headers=Headers({"content-type": content_type}),
    )
    return file


def make_request(headers: dict[str, str] | None = None) -> Request:
    """Return a minimal Starlette ``Request`` stub."""
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/upload",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    return Request(scope)


def make_form_data(fields: dict[str, UploadFile | list[UploadFile]] | None = None) -> FormData:
    """Build ``FormData`` from a mapping of field names to ``UploadFile``(s)."""
    items: list[tuple[str, Any]] = []
    for name, value in (fields or {}).items():
        if isinstance(value, list):
            for v in value:
                items.append((name, v))
        else:
            items.append((name, value))
    return FormData(items)


@pytest.fixture
def upload_file():
    """Yield a factory for ``UploadFile`` instances."""
    return make_upload_file


@pytest.fixture
def tmp_upload_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for local uploads."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir
