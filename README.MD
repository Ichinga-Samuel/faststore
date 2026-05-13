# filestore

[![PyPI version](https://badge.fury.io/py/filestore.svg)](https://pypi.org/project/filestore)
[![Python Versions](https://img.shields.io/pypi/pyversions/filestore.svg)](https://pypi.org/project/filestore)

`filestore` is a small FastAPI upload library with a simple dependency-based API and production-grade defaults.

It keeps the happy path short, but adds the things real services usually need:

- Safe local file writes with collision handling
- In-memory, S3, Google Cloud Storage, and Azure Blob Storage backends
- Multi-field upload support
- Async or sync callbacks for filenames, destinations, filters, and metadata
- File validation for size, extension, and content type
- Rich per-file results with aggregate helpers
- Optional S3 support that does not break the base install

## Installation

Install the base package:

```bash
pip install filestore
```

Install with S3 support:

```bash
pip install "filestore[s3]"
```

Install with Google Cloud Storage support:

```bash
pip install "filestore[gcp]"
```

Install with Azure Blob Storage support:

```bash
pip install "filestore[azure]"
```

## Quick Start

```python
from fastapi import Depends, FastAPI
from filestore import LocalStorage, Store

app = FastAPI()

storage = LocalStorage(
    name="file",
    required=True,
    config={"destination": "uploads", "base_url": "/media"},
)


@app.post("/upload")
async def upload(file_store: Store = Depends(storage)):
    file_data = file_store.first("file")
    return {
        "status": file_store.status,
        "filename": file_data.filename,
        "path": str(file_data.path),
        "url": file_data.url,
    }
```

`LocalStorage`, `MemoryStorage`, `S3Storage`, `GCSStorage`, and `AzureStorage` all use the same interface.

## Core API

### Single Field

```python
from filestore import MemoryStorage

storage = MemoryStorage(name="avatar", count=1, required=True)
```

### Multiple Fields

```python
from filestore import Config, FileField, FileStore

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            required=True,
            config=Config(destination="uploads/avatars"),
        ),
        FileField(
            name="resume",
            required=False,
            config=Config(destination="uploads/resumes"),
        ),
    ]
)
```

### Reading Results

The dependency returns a `Store` instance.

```python
store.status           # overall success
store.files            # dict[str, list[FileData]]
store.flat_files       # all files in one list
store.successful_files # only successful files
store.failed_files     # only failed files
store.total_files      # total count (successful + failed)
store.total_size       # sum of sizes for successful files
store.first("avatar")  # first file for a field, or None
store.error            # first aggregate error
store.errors           # all aggregate errors
```

Each `FileData` contains normalized metadata:

- `field_name`
- `filename`
- `original_filename`
- `path`
- `url`
- `file`
- `size`
- `content_type`
- `metadata`
- `status`
- `error`
- `message`
- `storage`

## Storage Backends

### Local Storage

Local storage writes to disk atomically and avoids overwriting existing files by default.

```python
from filestore import Config, LocalStorage

storage = LocalStorage(
    name="document",
    config=Config(
        destination="uploads/documents",
        base_url="/media/documents",
        overwrite=False,
    ),
)
```

### Memory Storage

Memory storage returns the raw bytes in `FileData.file`.

```python
from filestore import MemoryStorage

storage = MemoryStorage(name="image", count=3)
```

### S3 Storage

`S3Storage` uses the `s3` extra and works with AWS credentials from config or environment variables.

```python
from filestore import Config, S3Storage

storage = S3Storage(
    name="asset",
    config=Config(
        destination="uploads/assets",
        AWS_BUCKET_NAME="my-bucket",
        AWS_DEFAULT_REGION="us-east-1",
    ),
)
```

For S3-compatible services like MinIO or LocalStack, set `endpoint_url`.

### Google Cloud Storage

`GCSStorage` uses the `gcp` extra and works with Application Default Credentials or an explicit credentials object.

```python
from filestore import Config, GCSStorage

storage = GCSStorage(
    name="asset",
    config=Config(
        destination="uploads/assets",
        GCP_BUCKET_NAME="my-gcs-bucket",
        GCP_PROJECT="my-project-id",
    ),
)
```

Set `endpoint_url` if you want to target a compatible emulator or custom endpoint.

### Azure Blob Storage

`AzureStorage` uses the `azure` extra and supports either a connection string or an account URL plus credential.

```python
from filestore import AzureStorage, Config

storage = AzureStorage(
    name="asset",
    config=Config(
        destination="uploads/assets",
        AZURE_STORAGE_CONTAINER="my-container",
        AZURE_STORAGE_CONNECTION_STRING="UseDevelopmentStorage=true",
    ),
)
```

If you prefer passwordless auth, provide `AZURE_STORAGE_ACCOUNT_URL` and let the Azure SDK use `DefaultAzureCredential`.

## Validation and Callbacks

Every storage class accepts the same `config` keys.

### Validation

```python
from filestore import Config, LocalStorage

storage = LocalStorage(
    name="image",
    config=Config(
        destination="uploads/images",
        allowed_extensions=[".jpg", ".png"],
        allowed_content_types=["image/jpeg", "image/png"],
        max_file_size=5 * 1024 * 1024,
    ),
)
```

### Dynamic Destination

```python
from pathlib import Path
from filestore import Config, LocalStorage


async def destination(request, form, field_name, file):
    user_id = request.headers.get("X-User-ID", "anonymous")
    return Path("uploads") / user_id


storage = LocalStorage(
    name="file",
    config=Config(destination=destination),
)
```

### Dynamic Filename

The `filename` callback can return a string/path or an `UploadFile` whose `filename` has been updated.

```python
import uuid
from pathlib import Path
from filestore import Config, LocalStorage


def unique_name(request, form, field_name, file):
    suffix = Path(file.filename or "").suffix
    return f"reports/{uuid.uuid4()}{suffix}"


storage = LocalStorage(
    name="report",
    config=Config(destination="uploads", filename=unique_name),
)
```

### Filters

Filters may be sync or async. Return `True` to accept the file, `False` to reject it, or a string to reject it with a custom message.

```python
from filestore import Config, MemoryStorage


async def allow_text(request, form, field_name, file):
    if file.content_type == "text/plain":
        return True
    return "Only plain text files are allowed"


storage = MemoryStorage(
    name="notes",
    config=Config(filters=[allow_text]),
)
```

### Metadata

```python
from filestore import Config, LocalStorage


def extra_metadata(request, form, field_name, file):
    return {"request_id": request.headers.get("X-Request-ID")}


storage = LocalStorage(
    name="file",
    config=Config(destination="uploads", metadata=extra_metadata),
)
```

## Configuration Reference

Common config keys:

- `destination`: upload directory or cloud object/blob prefix. Can be sync or async.
- `filename`: override the stored filename. Can be sync or async.
- `filters`: one filter or a list of filters.
- `metadata`: extra per-file metadata. Can be sync or async.
- `allowed_extensions`: allowlist for file extensions.
- `allowed_content_types`: allowlist for MIME types.
- `max_file_size`: maximum size in bytes.
- `min_file_size`: minimum size in bytes.
- `max_files`: limit for multipart parsing.
- `max_fields`: limit for multipart parsing.
- `max_part_size`: limit for multipart parsing.
- `chunk_size`: local write chunk size.
- `overwrite`: whether local storage may overwrite existing files.
- `sanitize_filename`: normalize names and strip unsafe path segments.
- `base_url`: public URL prefix for local files.
- `extra_args`: extra keyword arguments passed to the storage backend upload call.
- `AWS_BUCKET_NAME`: S3 bucket name.
- `AWS_DEFAULT_REGION`: S3 region.
- `GCP_BUCKET_NAME`: Google Cloud Storage bucket name.
- `GCP_PROJECT`: Google Cloud project ID.
- `GCP_CREDENTIALS`: explicit Google credentials object.
- `AZURE_STORAGE_CONTAINER`: Azure Blob Storage container name.
- `AZURE_STORAGE_CONNECTION_STRING`: Azure Blob Storage connection string.
- `AZURE_STORAGE_ACCOUNT_URL`: Azure Blob Storage account URL.
- `AZURE_STORAGE_CREDENTIAL`: explicit Azure credential object.
- `endpoint_url`: optional cloud endpoint override for compatible services and emulators.

## Development

Run tests with:

```bash
uv run pytest
```

Build the package with:

```bash
uv build
```

## License

MIT
