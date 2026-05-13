"""End-to-end integration tests using httpx + FastAPI.

These tests exercise the full stack: HTTP request → multipart parsing →
validation → storage → Store response, with a real FastAPI application.
"""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest
from fastapi import Depends, FastAPI

from filestore import Config, FileField, LocalStorage, MemoryStorage, Store


def _build_app(storage, path: str = "/upload"):
    """Build a minimal FastAPI app with the given storage dependency."""
    app = FastAPI()

    @app.post(path)
    async def upload(store: Store = Depends(storage)):
        return store.to_dict()

    return app


# ── Memory storage integration ────────────────────────────────────────


class TestMemoryStorageIntegration:
    async def test_single_file_upload(self):
        storage = MemoryStorage(name="file", required=True)
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("hello.txt", b"hello world", "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["files"]["file"][0]["filename"] == "hello.txt"
        assert data["files"]["file"][0]["size"] == 11

    async def test_missing_required_field(self):
        storage = MemoryStorage(name="file", required=True)
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/upload")

        data = response.json()
        assert data["status"] is False
        assert any("Missing required" in e for e in data["errors"])

    async def test_optional_field_missing(self):
        storage = MemoryStorage(name="file", required=False)
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/upload")

        data = response.json()
        assert data["status"] is False  # no files uploaded at all

    async def test_multiple_files(self):
        storage = MemoryStorage(name="file", count=3)
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files=[
                    ("file", ("a.txt", b"aaa", "text/plain")),
                    ("file", ("b.txt", b"bbb", "text/plain")),
                ],
            )

        data = response.json()
        assert data["status"] is True
        assert len(data["files"]["file"]) == 2

    async def test_overflow_rejected(self):
        storage = MemoryStorage(name="file", count=1)
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files=[
                    ("file", ("a.txt", b"aaa", "text/plain")),
                    ("file", ("b.txt", b"bbb", "text/plain")),
                ],
            )

        data = response.json()
        assert data["status"] is False
        assert any("at most 1" in e for e in data["errors"])

    async def test_extension_validation(self):
        storage = MemoryStorage(
            name="file",
            config=Config(allowed_extensions=[".txt"]),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("script.exe", b"data", "application/octet-stream")},
            )

        data = response.json()
        assert data["status"] is False
        assert any("unsupported extension" in e for e in data["errors"])

    async def test_content_type_validation(self):
        storage = MemoryStorage(
            name="file",
            config=Config(allowed_content_types=["image/png"]),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("img.png", b"data", "text/html")},
            )

        data = response.json()
        assert data["status"] is False
        assert any("content type" in e for e in data["errors"])

    async def test_max_file_size(self):
        storage = MemoryStorage(
            name="file",
            config=Config(max_file_size=10),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("big.txt", b"x" * 100, "text/plain")},
            )

        data = response.json()
        assert data["status"] is False

    async def test_filter_rejection(self):
        def reject_all(request, form, field_name, file):
            return "Rejected by filter"

        storage = MemoryStorage(
            name="file",
            config=Config(filters=[reject_all]),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("test.txt", b"data", "text/plain")},
            )

        data = response.json()
        assert data["status"] is False
        assert any("Rejected by filter" in e for e in data["errors"])

    async def test_metadata_callback(self):
        def extra_meta(request, form, field_name, file):
            return {"source": "test"}

        storage = MemoryStorage(
            name="file",
            config=Config(metadata=extra_meta),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("test.txt", b"data", "text/plain")},
            )

        data = response.json()
        assert data["status"] is True
        assert data["files"]["file"][0]["metadata"]["source"] == "test"

    async def test_filename_callback(self):
        def custom_name(request, form, field_name, file):
            return "renamed.txt"

        storage = MemoryStorage(
            name="file",
            config=Config(filename=custom_name),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("original.txt", b"data", "text/plain")},
            )

        data = response.json()
        assert data["status"] is True
        assert data["files"]["file"][0]["filename"] == "renamed.txt"
        assert data["files"]["file"][0]["original_filename"] == "original.txt"


# ── Local storage integration ────────────────────────────────────────


class TestLocalStorageIntegration:
    async def test_local_upload(self, tmp_upload_dir: Path):
        storage = LocalStorage(
            name="file",
            config=Config(destination=str(tmp_upload_dir), base_url="/media"),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("report.pdf", b"pdf content", "application/pdf")},
            )

        data = response.json()
        assert data["status"] is True
        file_data = data["files"]["file"][0]
        assert file_data["filename"] == "report.pdf"
        assert file_data["url"] == "/media/report.pdf"
        assert (tmp_upload_dir / "report.pdf").exists()

    async def test_local_collision_handling(self, tmp_upload_dir: Path):
        storage = LocalStorage(
            name="file",
            config=Config(destination=str(tmp_upload_dir)),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # First upload
            await client.post(
                "/upload",
                files={"file": ("doc.txt", b"first", "text/plain")},
            )
            # Second upload with same name
            response = await client.post(
                "/upload",
                files={"file": ("doc.txt", b"second", "text/plain")},
            )

        data = response.json()
        assert data["status"] is True
        assert (tmp_upload_dir / "doc.txt").exists()
        assert (tmp_upload_dir / "doc-1.txt").exists()


# ── Multi-field integration ──────────────────────────────────────────


class TestMultiFieldIntegration:
    async def test_multi_field_upload(self):
        from filestore import FileStore

        storage = FileStore(
            fields=[
                FileField(name="avatar", required=True),
                FileField(name="resume"),
            ],
        )
        storage.StorageEngine = __import__("filestore").MemoryEngine

        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files=[
                    ("avatar", ("photo.png", b"png data", "image/png")),
                    ("resume", ("cv.pdf", b"pdf data", "application/pdf")),
                ],
            )

        data = response.json()
        assert data["status"] is True
        assert len(data["files"]["avatar"]) == 1
        assert len(data["files"]["resume"]) == 1

    async def test_multi_field_partial_failure(self):
        from filestore import FileStore

        storage = FileStore(
            fields=[
                FileField(
                    name="avatar",
                    required=True,
                    config=Config(allowed_extensions=[".png"]),
                ),
                FileField(name="document"),
            ],
        )
        storage.StorageEngine = __import__("filestore").MemoryEngine

        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files=[
                    ("avatar", ("photo.exe", b"bad", "application/octet-stream")),
                    ("document", ("doc.txt", b"good", "text/plain")),
                ],
            )

        data = response.json()
        assert data["status"] is False
        assert "Some files failed" in data["message"]


# ── Dynamic destination integration ──────────────────────────────────


class TestDynamicDestination:
    async def test_callable_destination(self, tmp_path: Path):
        user_dir = tmp_path / "user123"

        async def destination(request, form, field_name, file):
            return str(user_dir)

        storage = LocalStorage(
            name="file",
            config=Config(destination=destination),
        )
        app = _build_app(storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/upload",
                files={"file": ("test.txt", b"data", "text/plain")},
            )

        data = response.json()
        assert data["status"] is True
        assert user_dir.exists()
        assert (user_dir / "test.txt").exists()
