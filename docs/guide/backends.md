# Storage Backends

Faststore ships with five storage backends. All share the same API — you can switch backends by changing a single class name.

## Local Storage

Writes files to the local filesystem. This is the default backend.

```python
from filestore import Config, LocalStorage

storage = LocalStorage(
    name="document",
    config=Config(
        destination="uploads/documents",
        base_url="/media/documents",
    ),
)
```

### Features

- **Atomic writes** — files are written to a temporary file first, then renamed into place. No partial uploads on crash.
- **Collision handling** — when `overwrite=False` (the default), a numeric suffix is appended: `doc.pdf` → `doc-1.pdf` → `doc-2.pdf`.
- **Directory creation** — destination directories are created automatically.
- **Chunked I/O** — large files are written in chunks (default 1 MiB). Customize with `chunk_size`.

### Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `destination` | `str \| Path \| callable` | Current directory | Target directory for uploads |
| `base_url` | `str` | `None` | Public URL prefix for `FileData.url` |
| `overwrite` | `bool` | `False` | Whether to overwrite existing files |
| `chunk_size` | `int` | `1048576` | Read/write chunk size in bytes |
| `sanitize_filename` | `bool` | `True` | Replace unsafe characters with underscores |

### Result

The returned `FileData` includes:

- `path` — absolute `Path` to the written file
- `url` — public URL (if `base_url` was set)
- `metadata["relative_path"]` — path relative to the destination

---

## Memory Storage

Reads the entire file into memory. No disk I/O. Useful for pipelines that process the payload without persisting it.

```python
from filestore import MemoryStorage

storage = MemoryStorage(name="image", count=3)
```

### Result

- `file` — the raw `bytes` payload
- `path` is `None`
- `url` is `None`

---

## S3 Storage

Upload to Amazon S3 or any S3-compatible service (MinIO, LocalStack, DigitalOcean Spaces, etc.).

!!! note "Requires extra"
    Install with `pip install "filestore[s3]"`

```python
from filestore import Config, S3Storage

storage = S3Storage(
    name="asset",
    config=Config(
        destination="uploads/assets",     # S3 key prefix
        AWS_BUCKET_NAME="my-bucket",
        AWS_DEFAULT_REGION="us-east-1",
    ),
)
```

### Credentials

Credentials are resolved in order:

1. Standard `boto3` credential chain (environment variables, `~/.aws/credentials`, IAM role, etc.)

Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables, or rely on IAM roles in production.

### S3-Compatible Services

```python
storage = S3Storage(
    name="asset",
    config=Config(
        destination="uploads",
        AWS_BUCKET_NAME="my-bucket",
        endpoint_url="http://localhost:9000",  # MinIO
    ),
)
```

### Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AWS_BUCKET_NAME` | `str` | — | **Required.** S3 bucket name |
| `AWS_DEFAULT_REGION` | `str` | env var | AWS region |
| `endpoint_url` | `str` | `None` | Custom endpoint for S3-compatible services |
| `extra_args` | `dict` | `{}` | Extra kwargs passed to `put_object()` |

### Result

- `url` — public S3 URL
- `metadata["bucket"]` — bucket name
- `metadata["key"]` — full S3 object key

---

## Google Cloud Storage

Upload to GCS buckets.

!!! note "Requires extra"
    Install with `pip install "filestore[gcp]"`

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

### Credentials

Uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) by default. Pass `GCP_CREDENTIALS` in config for explicit credentials.

### Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `GCP_BUCKET_NAME` | `str` | — | **Required.** GCS bucket name |
| `GCP_PROJECT` | `str` | env var | Google Cloud project ID |
| `GCP_CREDENTIALS` | `object` | ADC | Explicit credentials object |
| `endpoint_url` | `str` | `None` | Custom endpoint for emulators |
| `overwrite` | `bool` | `False` | When `False`, uses `if_generation_match=0` to prevent overwrites |

### Result

- `url` — public GCS URL
- `metadata["bucket"]` — bucket name
- `metadata["key"]` — full object key

---

## Azure Blob Storage

Upload to Azure Blob Storage containers.

!!! note "Requires extra"
    Install with `pip install "filestore[azure]"`

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

### Authentication

Azure supports two authentication modes:

=== "Connection String"

    ```python
    config = Config(
        AZURE_STORAGE_CONTAINER="my-container",
        AZURE_STORAGE_CONNECTION_STRING="DefaultEndpoints...",
    )
    ```

=== "Account URL + Managed Identity"

    ```python
    config = Config(
        AZURE_STORAGE_CONTAINER="my-container",
        AZURE_STORAGE_ACCOUNT_URL="https://myaccount.blob.core.windows.net",
        # Uses DefaultAzureCredential automatically
    )
    ```

### Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AZURE_STORAGE_CONTAINER` | `str` | — | **Required.** Blob container name |
| `AZURE_STORAGE_CONNECTION_STRING` | `str` | env var | Connection string auth |
| `AZURE_STORAGE_ACCOUNT_URL` | `str` | env var | Account URL for managed identity |
| `AZURE_STORAGE_CREDENTIAL` | `object` | auto | Explicit credential object |
| `overwrite` | `bool` | `False` | Whether to overwrite existing blobs |

### Result

- `url` — blob URL
- `metadata["container"]` — container name
- `metadata["blob"]` — full blob name
- `metadata["etag"]` — ETag (when available)
