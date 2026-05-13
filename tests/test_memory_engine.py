"""Tests for the MemoryEngine storage backend."""

from __future__ import annotations

import io

import pytest
from starlette.datastructures import Headers, UploadFile

from filestore import FileData, FileField, MemoryEngine, ValidationError
from filestore.exceptions import StorageError

from conftest import make_form_data, make_request, make_upload_file


class TestMemoryEngine:
    def _make_engine(self, fields=None):
        request = make_request()
        form = make_form_data(fields)
        return MemoryEngine(request=request, form=form)

    async def test_basic_upload(self):
        engine = self._make_engine()
        file = make_upload_file(b"hello world", "test.txt", "text/plain")
        field = FileField(name="file")

        result = await engine.upload(field, file)

        assert isinstance(result, FileData)
        assert result.status is True
        assert result.file == b"hello world"
        assert result.size == 11
        assert result.filename == "test.txt"
        assert result.content_type == "text/plain"
        assert result.storage == "memory"

    async def test_upload_binary(self):
        engine = self._make_engine()
        data = bytes(range(256))
        file = make_upload_file(data, "binary.bin", "application/octet-stream")
        field = FileField(name="file")

        result = await engine.upload(field, file)
        assert result.file == data
        assert result.size == 256

    async def test_upload_empty_file(self):
        engine = self._make_engine()
        file = make_upload_file(b"", "empty.txt")
        field = FileField(name="file")

        result = await engine.upload(field, file)
        assert result.status is True
        assert result.file == b""
        assert result.size == 0

    async def test_max_file_size_rejected(self):
        engine = self._make_engine()
        file = make_upload_file(b"x" * 100, "big.txt")
        field = FileField(name="file", config={"max_file_size": 50})

        with pytest.raises(ValidationError, match="exceeds the maximum"):
            await engine.upload(field, file)

    async def test_min_file_size_rejected(self):
        engine = self._make_engine()
        file = make_upload_file(b"hi", "small.txt")
        field = FileField(name="file", config={"min_file_size": 100})

        with pytest.raises(ValidationError, match="smaller than the minimum"):
            await engine.upload(field, file)

    async def test_sanitize_filename(self):
        engine = self._make_engine()
        file = make_upload_file(b"data", "my file (1).txt")
        field = FileField(name="file")

        result = await engine.upload(field, file)
        assert " " not in result.filename
        assert "(" not in result.filename

    async def test_sanitize_filename_disabled(self):
        engine = self._make_engine()
        file = make_upload_file(b"data", "my file.txt")
        field = FileField(name="file", config={"sanitize_filename": False})

        result = await engine.upload(field, file)
        assert result.filename == "my file.txt"

    async def test_message_format(self):
        engine = self._make_engine()
        file = make_upload_file(b"data", "report.pdf")
        field = FileField(name="file")

        result = await engine.upload(field, file)
        assert "report.pdf" in result.message
        assert "uploaded successfully" in result.message

    async def test_upload_with_no_filename(self):
        engine = self._make_engine()
        file = UploadFile(
            file=io.BytesIO(b"content"),
            filename=None,
            size=7,
        )
        field = FileField(name="file")

        result = await engine.upload(field, file)
        assert result.status is True
        assert result.filename == "upload"
