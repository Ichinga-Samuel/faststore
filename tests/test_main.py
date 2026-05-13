"""Tests for filestore.main — FileStore orchestration.

These tests verify the full pipeline: field parsing, validation,
filtering, filename resolution, and store assembly, using the
MemoryEngine to avoid filesystem dependencies.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.requests import Request

from filestore import (
    Config,
    ConfigurationError,
    FileData,
    FileField,
    FileStore,
    MemoryStorage,
    Store,
    ValidationError,
)
from filestore.main import PreparedUpload

from conftest import make_form_data, make_request, make_upload_file


# ── FileStore construction ────────────────────────────────────────────


class TestFileStoreConstruction:
    def test_single_field_shorthand(self):
        store = FileStore(name="avatar", count=3, required=True)
        assert len(store.fields) == 1
        assert store.fields[0].name == "avatar"
        assert store.fields[0].max_count == 3
        assert store.fields[0].required is True

    def test_explicit_fields(self):
        fields = [
            FileField(name="avatar", required=True),
            FileField(name="resume"),
        ]
        store = FileStore(fields=fields)
        assert len(store.fields) == 2

    def test_mixed_name_and_fields(self):
        store = FileStore(
            name="photo",
            fields=[FileField(name="document")],
        )
        assert len(store.fields) == 2

    def test_duplicate_field_names_raise(self):
        with pytest.raises(ConfigurationError, match="Duplicate"):
            FileStore(fields=[
                FileField(name="file"),
                FileField(name="file"),
            ])

    def test_no_fields_no_error(self):
        store = FileStore()
        assert store.fields == []

    def test_config_normalized(self):
        store = FileStore(name="file", config={"destination": "uploads"})
        assert store.config == {"destination": "uploads"}

    def test_none_config(self):
        store = FileStore(name="file", config=None)
        assert store.config == {}


# ── Config merging ────────────────────────────────────────────────────


class TestConfigMerging:
    def test_field_config_overrides_store(self):
        store = FileStore(
            name="file",
            config={"destination": "base", "max_file_size": 100},
        )
        store.fields[0].config = {"destination": "override"}
        merged = store._merge_config(store.fields[0])
        assert merged["destination"] == "override"
        assert merged["max_file_size"] == 100

    def test_filters_concatenated(self):
        fn1 = lambda r, f, n, file: True
        fn2 = lambda r, f, n, file: True
        store = FileStore(
            name="file",
            config={"filters": fn1},
        )
        store.fields[0].config = {"filters": fn2}
        merged = store._merge_config(store.fields[0])
        assert merged["filters"] == [fn1, fn2]


# ── Validation ────────────────────────────────────────────────────────


class TestValidation:
    def test_extension_validation_accepted(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "image.png", "image/png")
        field = FileField(name="file", config={"allowed_extensions": [".png", ".jpg"]})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is None

    def test_extension_validation_rejected(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "script.exe", "application/octet-stream")
        field = FileField(name="file", config={"allowed_extensions": [".png", ".jpg"]})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is not None
        assert "unsupported extension" in result

    def test_content_type_validation_accepted(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "img.png", "image/png")
        field = FileField(name="file", config={"allowed_content_types": ["image/png"]})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is None

    def test_content_type_validation_rejected(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "img.png", "text/html")
        field = FileField(name="file", config={"allowed_content_types": ["image/png"]})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is not None
        assert "content type" in result

    def test_extension_without_dot(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "image.png")
        field = FileField(name="file", config={"allowed_extensions": ["png"]})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is None

    def test_string_extensions(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "image.png")
        field = FileField(name="file", config={"allowed_extensions": ".png"})
        result = store._validate_type_constraints(file_field=field, file=file, config=field.config)
        assert result is None


# ── Filters ───────────────────────────────────────────────────────────


class TestFilters:
    async def test_filter_accept(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file", config={"filters": [lambda r, f, n, file: True]})
        result = await store._run_filters(
            config=field.config,
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result is None

    async def test_filter_reject_with_message(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file", config={"filters": [lambda r, f, n, file: "Not allowed"]})
        result = await store._run_filters(
            config=field.config,
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result == "Not allowed"

    async def test_filter_reject_with_false(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file", config={"filters": [lambda r, f, n, file: False]})
        result = await store._run_filters(
            config=field.config,
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result is not None
        assert "rejected" in result

    async def test_async_filter(self):
        async def my_filter(request, form, field_name, file):
            return True

        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file", config={"filters": [my_filter]})
        result = await store._run_filters(
            config=field.config,
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result is None

    async def test_multiple_filters_first_rejection_wins(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(
            name="file",
            config={"filters": [
                lambda r, f, n, file: True,
                lambda r, f, n, file: "Second filter rejects",
                lambda r, f, n, file: "Third filter (never reached)",
            ]},
        )
        result = await store._run_filters(
            config=field.config,
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result == "Second filter rejects"


# ── Filename resolution ──────────────────────────────────────────────


class TestFilenameResolution:
    async def test_default_filename(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "original.txt")
        field = FileField(name="file")
        resolved_file, filename = await store._resolve_filename(
            config={},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert filename == "original.txt"

    async def test_static_filename_override(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "original.txt")
        field = FileField(name="file")
        _, filename = await store._resolve_filename(
            config={"filename": "renamed.txt"},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert filename == "renamed.txt"

    async def test_callable_filename(self):
        def my_filename(request, form, field_name, file):
            return "custom.txt"

        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "original.txt")
        field = FileField(name="file")
        _, filename = await store._resolve_filename(
            config={"filename": my_filename},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert filename == "custom.txt"

    async def test_async_callable_filename(self):
        async def my_filename(request, form, field_name, file):
            return "async_custom.txt"

        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "original.txt")
        field = FileField(name="file")
        _, filename = await store._resolve_filename(
            config={"filename": my_filename},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert filename == "async_custom.txt"


# ── Metadata resolution ──────────────────────────────────────────────


class TestMetadataResolution:
    async def test_no_metadata(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file")
        result = await store._resolve_metadata(
            config={},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result == {}

    async def test_static_metadata(self):
        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file")
        result = await store._resolve_metadata(
            config={"metadata": {"key": "value"}},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result == {"key": "value"}

    async def test_callable_metadata(self):
        def my_metadata(request, form, field_name, file):
            return {"from": "callback"}

        store = MemoryStorage(name="file")
        file = make_upload_file(b"data", "test.txt")
        field = FileField(name="file")
        result = await store._resolve_metadata(
            config={"metadata": my_metadata},
            request=make_request(),
            form=make_form_data(),
            file_field=field,
            file=file,
        )
        assert result == {"from": "callback"}


# ── build_store ──────────────────────────────────────────────────────


class TestBuildStore:
    def test_all_success(self):
        results = [
            [FileData(field_name="a", status=True, filename="a.txt", message="ok")],
        ]
        store = FileStore.build_store(results)
        assert store.status is True
        assert store.total_files == 1
        assert len(store.successful_files) == 1

    def test_all_failures(self):
        results = [
            [FileData(field_name="a", status=False, error="bad", message="bad")],
        ]
        store = FileStore.build_store(results)
        assert store.status is False
        assert len(store.failed_files) == 1

    def test_mixed_results(self):
        results = [
            [
                FileData(field_name="a", status=True, message="ok"),
                FileData(field_name="a", status=False, error="fail", message="fail"),
            ],
        ]
        store = FileStore.build_store(results)
        assert store.status is False
        assert store.total_files == 2
        assert "Some files failed" in store.message

    def test_empty_results(self):
        store = FileStore.build_store([])
        assert store.status is False
        assert "No files" in store.message

    def test_exception_in_results(self):
        results = [RuntimeError("boom")]
        store = FileStore.build_store(results)
        assert store.status is False
        assert "boom" in store.errors[0]

    def test_nested_lists(self):
        results = [
            [
                FileData(field_name="a", status=True, message="ok"),
            ],
            [
                FileData(field_name="b", status=True, message="ok"),
            ],
        ]
        store = FileStore.build_store(results)
        assert store.total_files == 2
        assert store.status is True


# ── handle() — the critical bug-fix test ─────────────────────────────


class TestHandleMethod:
    """Verify that handle() returns BOTH successes and failures.

    This was the critical bug: the old code only returned failures,
    silently dropping successful FileData results.
    """

    async def test_successful_upload_returned(self):
        storage = MemoryStorage(name="file")
        file = make_upload_file(b"hello", "test.txt")
        form = make_form_data({"file": file})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        successes = [r for r in results if r.status]
        assert len(successes) == 1
        assert successes[0].filename == "test.txt"

    async def test_mixed_success_and_failure(self):
        storage = MemoryStorage(
            name="file",
            count=5,
            config={"allowed_extensions": [".txt"]},
        )
        files = [
            make_upload_file(b"ok", "good.txt"),
            make_upload_file(b"bad", "bad.exe"),
        ]
        form = make_form_data({"file": files})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        successes = [r for r in results if r.status]
        failures = [r for r in results if not r.status]
        assert len(successes) == 1
        assert len(failures) == 1

    async def test_required_field_missing(self):
        storage = MemoryStorage(name="file", required=True)
        form = make_form_data({})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        assert len(results) == 1
        assert results[0].status is False
        assert "Missing required" in results[0].error

    async def test_optional_field_missing(self):
        storage = MemoryStorage(name="file", required=False)
        form = make_form_data({})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        assert results == []

    async def test_overflow_files_rejected(self):
        storage = MemoryStorage(name="file", count=1)
        files = [
            make_upload_file(b"first", "a.txt"),
            make_upload_file(b"second", "b.txt"),
        ]
        form = make_form_data({"file": files})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        successes = [r for r in results if r.status]
        failures = [r for r in results if not r.status]
        assert len(successes) == 1
        assert len(failures) == 1
        assert "at most 1" in failures[0].error

    async def test_multiple_files_all_success(self):
        storage = MemoryStorage(name="file", count=3)
        files = [
            make_upload_file(b"one", "a.txt"),
            make_upload_file(b"two", "b.txt"),
            make_upload_file(b"three", "c.txt"),
        ]
        form = make_form_data({"file": files})
        request = make_request()

        results = await storage.handle(
            file_field=storage.fields[0],
            request=request,
            form=form,
        )

        assert all(r.status for r in results)
        assert len(results) == 3


# ── __call__ end-to-end ──────────────────────────────────────────────


class TestCallEndToEnd:
    async def test_no_fields_configured(self):
        storage = FileStore()
        request = make_request()
        # Mock request.form to avoid actual parsing
        request._form = make_form_data({})
        store = await storage(request)
        assert store.status is False
        assert "No file fields" in store.message

    async def test_single_successful_upload(self):
        storage = MemoryStorage(name="file")
        file = make_upload_file(b"content", "doc.txt")
        request = make_request()
        form = make_form_data({"file": file})

        # Patch request.form() to return our test form
        async def mock_form(**kwargs):
            return form

        request.form = mock_form

        store = await storage(request)
        assert store.status is True
        assert store.total_files == 1
        first = store.first("file")
        assert first is not None
        assert first.status is True

    async def test_multiple_fields(self):
        storage = FileStore(fields=[
            FileField(name="avatar", required=True),
            FileField(name="resume"),
        ])
        storage.StorageEngine = __import__("filestore").MemoryEngine

        avatar = make_upload_file(b"avatar data", "avatar.png", "image/png")
        resume = make_upload_file(b"resume data", "resume.pdf", "application/pdf")
        form = make_form_data({"avatar": avatar, "resume": resume})
        request = make_request()

        async def mock_form(**kwargs):
            return form

        request.form = mock_form

        store = await storage(request)
        assert store.total_files == 2
        assert store.first("avatar") is not None
        assert store.first("resume") is not None

    async def test_exception_in_form_parsing(self):
        storage = MemoryStorage(name="file")
        request = make_request()

        async def boom(**kwargs):
            raise RuntimeError("parse error")

        request.form = boom

        store = await storage(request)
        assert store.status is False
        assert "parse error" in store.error


# ── Engine creation ──────────────────────────────────────────────────


class TestEngineCreation:
    def test_invalid_engine_class(self):
        storage = MemoryStorage(name="file")
        with pytest.raises(ConfigurationError, match="must be a StorageEngine subclass"):
            storage._create_engine(
                config={"StorageEngine": str},
                request=make_request(),
                form=make_form_data(),
            )

    def test_none_engine_class(self):
        storage = MemoryStorage(name="file")
        with pytest.raises(ConfigurationError, match="must be configured"):
            storage._create_engine(
                config={"StorageEngine": None},
                request=make_request(),
                form=make_form_data(),
            )


# ── Storage class wrappers ───────────────────────────────────────────


class TestStorageClasses:
    def test_memory_storage_engine(self):
        from filestore import MemoryEngine

        storage = MemoryStorage(name="file")
        assert storage.StorageEngine is MemoryEngine

    def test_local_storage_engine(self):
        from filestore import LocalEngine, LocalStorage

        storage = LocalStorage(name="file")
        assert storage.StorageEngine is LocalEngine

    def test_s3_storage_engine(self):
        from filestore import S3Storage
        from filestore.storage_engines.s3_engine import S3Engine

        storage = S3Storage(name="file")
        assert storage.StorageEngine is S3Engine

    def test_gcs_storage_engine(self):
        from filestore import GCSStorage
        from filestore.storage_engines.gcs_engine import GCSEngine

        storage = GCSStorage(name="file")
        assert storage.StorageEngine is GCSEngine

    def test_azure_storage_engine(self):
        from filestore import AzureStorage
        from filestore.storage_engines.azure_engine import AzureBlobEngine

        storage = AzureStorage(name="file")
        assert storage.StorageEngine is AzureBlobEngine
