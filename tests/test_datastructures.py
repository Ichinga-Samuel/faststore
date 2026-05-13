"""Tests for filestore.datastructures — FileField, FileData, Store, Config."""

from __future__ import annotations

import pytest

from filestore import Config, FileData, FileField, Store

# ── FileField ─────────────────────────────────────────────────────────


class TestFileField:
    def test_basic_construction(self):
        field = FileField(name="avatar")
        assert field.name == "avatar"
        assert field.max_count == 1
        assert field.required is False
        assert field.config == {}

    def test_with_options(self):
        field = FileField(name="resume", max_count=3, required=True)
        assert field.max_count == 3
        assert field.required is True

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            FileField(name="")

    def test_zero_max_count_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            FileField(name="file", max_count=0)

    def test_negative_max_count_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            FileField(name="file", max_count=-1)

    def test_config_is_copied(self):
        original: Config = {"destination": "uploads"}
        field = FileField(name="file", config=original)
        field.config["destination"] = "changed"
        assert original["destination"] == "uploads"

    def test_none_config_becomes_empty_dict(self):
        field = FileField(name="file", config=None)
        assert field.config == {}

    def test_repr(self):
        field = FileField(name="avatar", max_count=3, required=True)
        r = repr(field)
        assert "avatar" in r
        assert "max_count=3" in r
        assert "required=True" in r


# ── FileData ──────────────────────────────────────────────────────────


class TestFileData:
    def test_default_values(self):
        fd = FileData(field_name="file")
        assert fd.field_name == "file"
        assert fd.status is False
        assert fd.path is None
        assert fd.url is None
        assert fd.size is None
        assert fd.file is None
        assert fd.metadata == {}
        assert fd.error is None

    def test_location_prefers_url(self):
        from pathlib import Path

        fd = FileData(field_name="f", url="https://example.com/file.txt", path=Path("/tmp/file.txt"))
        assert fd.location == "https://example.com/file.txt"

    def test_location_falls_back_to_path(self):
        from pathlib import Path

        fd = FileData(field_name="f", path=Path("/tmp/file.txt"))
        assert fd.location == Path("/tmp/file.txt")

    def test_location_none_when_empty(self):
        fd = FileData(field_name="f")
        assert fd.location is None

    def test_to_dict_serializes_path(self):
        from pathlib import Path

        fd = FileData(field_name="f", path=Path("/uploads/test.txt"), status=True)
        d = fd.to_dict()
        assert isinstance(d["path"], str)
        assert "test.txt" in d["path"]

    def test_to_dict_handles_bytes(self):
        fd = FileData(field_name="f", file=b"some data", status=True)
        d = fd.to_dict()
        assert d["file"] == "<9 bytes>"

    def test_to_dict_without_bytes(self):
        fd = FileData(field_name="f", status=True)
        d = fd.to_dict()
        assert d["file"] is None

    def test_repr(self):
        fd = FileData(field_name="avatar", filename="img.png", status=True, size=1234)
        r = repr(fd)
        assert "avatar" in r
        assert "img.png" in r
        assert "ok" in r
        assert "1234" in r

    def test_repr_failed(self):
        fd = FileData(field_name="file", filename="bad.exe", status=False)
        r = repr(fd)
        assert "failed" in r


# ── Store ─────────────────────────────────────────────────────────────


class TestStore:
    def test_empty_store(self):
        store = Store()
        assert store.status is True
        assert store.total_files == 0
        assert store.flat_files == []
        assert store.successful_files == []
        assert store.failed_files == []
        assert store.total_size == 0

    def test_add_successful_file(self):
        store = Store()
        fd = FileData(field_name="avatar", filename="img.png", status=True, size=100, message="ok")
        store.add(fd)
        assert store.total_files == 1
        assert store.files["avatar"] == [fd]
        assert fd in store.successful_files
        assert fd not in store.failed_files
        assert "ok" in store.messages

    def test_add_failed_file(self):
        store = Store()
        fd = FileData(field_name="file", status=False, error="too big", message="too big")
        store.add(fd)
        assert store.total_files == 1
        assert fd in store.failed_files
        assert "too big" in store.errors

    def test_mixed_files(self):
        store = Store()
        ok = FileData(field_name="a", status=True, size=50, message="ok")
        fail = FileData(field_name="b", status=False, error="nope", message="nope")
        store.add(ok)
        store.add(fail)
        assert store.total_files == 2
        assert len(store.successful_files) == 1
        assert len(store.failed_files) == 1

    def test_total_size_only_counts_successes(self):
        store = Store()
        store.add(FileData(field_name="a", status=True, size=100))
        store.add(FileData(field_name="b", status=False, size=200))
        store.add(FileData(field_name="c", status=True, size=None))
        assert store.total_size == 100

    def test_first_returns_none_for_missing(self):
        store = Store()
        assert store.first("nonexistent") is None

    def test_first_returns_first(self):
        store = Store()
        fd1 = FileData(field_name="avatar", filename="a.png", status=True)
        fd2 = FileData(field_name="avatar", filename="b.png", status=True)
        store.add(fd1)
        store.add(fd2)
        assert store.first("avatar") is fd1

    def test_to_dict(self):
        store = Store()
        store.add(FileData(field_name="f", filename="x.txt", status=True))
        d = store.to_dict()
        assert "files" in d
        assert "f" in d["files"]
        assert isinstance(d["files"]["f"], list)
        assert d["status"] is True

    def test_repr(self):
        store = Store()
        store.add(FileData(field_name="a", status=True))
        store.add(FileData(field_name="b", status=False))
        r = repr(store)
        assert "total=2" in r
        assert "ok=1" in r
        assert "failed=1" in r

    def test_multiple_fields_flat_files(self):
        store = Store()
        fd1 = FileData(field_name="avatar", status=True)
        fd2 = FileData(field_name="resume", status=True)
        fd3 = FileData(field_name="avatar", status=True)
        store.add(fd1)
        store.add(fd2)
        store.add(fd3)
        assert len(store.flat_files) == 3
        assert len(store.files["avatar"]) == 2
        assert len(store.files["resume"]) == 1
