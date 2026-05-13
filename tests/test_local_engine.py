"""Tests for the LocalEngine storage backend."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from filestore import FileData, FileField, LocalEngine, ValidationError
from filestore.exceptions import StorageError

from conftest import make_form_data, make_request, make_upload_file


class TestLocalEngine:
    def _make_engine(self):
        return LocalEngine(request=make_request(), form=make_form_data())

    async def test_basic_upload(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"hello world", "test.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})

        result = await engine.upload(field, file)

        assert result.status is True
        assert result.filename == "test.txt"
        assert result.size == 11
        assert result.path is not None
        assert result.path.exists()
        assert result.path.read_bytes() == b"hello world"
        assert result.storage == "local"

    async def test_creates_destination_directory(self, tmp_path: Path):
        engine = self._make_engine()
        dest = tmp_path / "new_dir" / "nested"
        file = make_upload_file(b"data", "file.txt")
        field = FileField(name="file", config={"destination": str(dest)})

        result = await engine.upload(field, file)
        assert result.status is True
        assert result.path.parent == dest

    async def test_no_overwrite_renames(self, tmp_upload_dir: Path):
        engine = self._make_engine()

        # Create first file
        file1 = make_upload_file(b"first", "doc.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})
        result1 = await engine.upload(field, file1)

        # Upload again with same name
        engine2 = self._make_engine()
        file2 = make_upload_file(b"second", "doc.txt")
        result2 = await engine2.upload(field, file2)

        assert result1.path != result2.path
        assert result2.path.name == "doc-1.txt"
        assert result1.path.read_bytes() == b"first"
        assert result2.path.read_bytes() == b"second"

    async def test_overwrite_replaces(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file1 = make_upload_file(b"first", "doc.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir), "overwrite": True})
        await engine.upload(field, file1)

        engine2 = self._make_engine()
        file2 = make_upload_file(b"replaced", "doc.txt")
        result2 = await engine2.upload(field, file2)

        assert result2.path.read_bytes() == b"replaced"

    async def test_max_file_size_rejected(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"x" * 100, "big.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir), "max_file_size": 50})

        with pytest.raises(ValidationError, match="exceeds"):
            await engine.upload(field, file)

    async def test_min_file_size_rejected(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"hi", "small.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir), "min_file_size": 100})

        with pytest.raises(ValidationError, match="smaller"):
            await engine.upload(field, file)

    async def test_base_url_sets_url(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"data", "report.pdf")
        field = FileField(
            name="file",
            config={"destination": str(tmp_upload_dir), "base_url": "/media"},
        )
        result = await engine.upload(field, file)
        assert result.url == "/media/report.pdf"

    async def test_no_base_url_no_url(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"data", "report.pdf")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})
        result = await engine.upload(field, file)
        assert result.url is None

    async def test_subdirectory_in_filename(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"data", "docs/report.pdf")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})
        result = await engine.upload(field, file)
        assert result.status is True
        assert result.path.exists()
        assert "docs" in str(result.path)

    async def test_cleanup_on_validation_failure(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"x" * 200, "big.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir), "max_file_size": 50})

        with pytest.raises(ValidationError):
            await engine.upload(field, file)

        # Ensure no temp files remain
        remaining = list(tmp_upload_dir.glob("*"))
        assert len(remaining) == 0

    async def test_metadata_includes_relative_path(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})
        result = await engine.upload(field, file)
        assert "relative_path" in result.metadata
        assert result.metadata["relative_path"] == "test.txt"

    async def test_custom_chunk_size(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"a" * 1000, "chunked.txt")
        field = FileField(
            name="file",
            config={"destination": str(tmp_upload_dir), "chunk_size": 100},
        )
        result = await engine.upload(field, file)
        assert result.status is True
        assert result.size == 1000

    async def test_sanitize_filename(self, tmp_upload_dir: Path):
        engine = self._make_engine()
        file = make_upload_file(b"data", "my file (v2).txt")
        field = FileField(name="file", config={"destination": str(tmp_upload_dir)})
        result = await engine.upload(field, file)
        assert " " not in result.path.name
        assert "(" not in result.path.name
