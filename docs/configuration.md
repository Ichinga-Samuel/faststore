# Configuration Reference

Complete reference for all configuration keys accepted by `Config`.

## How Config Works

Config is a `TypedDict` with all optional keys. It can be set at two levels:

1. **Store level** — applies to all fields as a baseline
2. **Field level** — overrides the store level for that specific field

```python
from filestore import Config, FileField, FileStore

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            config=Config(max_file_size=2 * 1024 * 1024),  # Field override
        ),
    ],
    config=Config(max_file_size=10 * 1024 * 1024),  # Store baseline
)
```

!!! info "Filter merging"
    Filters are the one exception — store-level and field-level filters are **concatenated**, not overridden. Store filters run first.

## All Configuration Keys

### General

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `destination` | `str \| Path \| callable` | CWD | Upload directory (local) or key prefix (cloud). Callable receives `(request, form, field_name, file)`. |
| `filename` | `str \| Path \| callable` | Original | Override stored filename. Callable receives `(request, form, field_name, file)`. |
| `filters` | `list[callable] \| callable` | `[]` | One or more filter callbacks. Return `True` to accept, `False` or a string to reject. |
| `metadata` | `dict \| callable` | `{}` | Static metadata dict or callback. Merged into `FileData.metadata`. |
| `extra_args` | `dict` | `{}` | Extra kwargs passed to the backend upload call (e.g., S3 `put_object()` kwargs). |

### Validation

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_file_size` | `int` | Unlimited | Maximum file size in bytes. |
| `min_file_size` | `int` | `0` | Minimum file size in bytes. |
| `allowed_extensions` | `list[str]` | All | Allowed file extensions. Case-insensitive. Leading dot optional. |
| `allowed_content_types` | `list[str]` | All | Allowed MIME types. Case-insensitive. |

### Multipart Parsing

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_files` | `int` | `1000` | Maximum number of files in the multipart body. |
| `max_fields` | `int` | `1000` | Maximum number of form fields. |
| `max_part_size` | `int` | `1048576` | Maximum size of a single multipart part (bytes). |

### Local Storage

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `chunk_size` | `int` | `1048576` | Read/write chunk size in bytes. |
| `overwrite` | `bool` | `False` | Whether to overwrite existing files. When `False`, adds a numeric suffix. |
| `sanitize_filename` | `bool` | `True` | Replace unsafe characters (`[^A-Za-z0-9._-]`) with underscores. |
| `base_url` | `str` | `None` | Public URL prefix. When set, `FileData.url` is populated. |

### Cloud Common

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `endpoint_url` | `str` | `None` | Custom endpoint for S3-compatible services, GCS emulators, etc. |

### Amazon S3

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AWS_BUCKET_NAME` | `str` | Env var | **Required.** S3 bucket name. Falls back to `AWS_BUCKET_NAME` env var. |
| `AWS_DEFAULT_REGION` | `str` | Env var | AWS region. Falls back to `AWS_DEFAULT_REGION` env var. |

### Google Cloud Storage

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `GCP_BUCKET_NAME` | `str` | Env var | **Required.** GCS bucket name. Falls back to `GCP_BUCKET_NAME` env var. |
| `GCP_PROJECT` | `str` | Env var | Google Cloud project ID. Falls back to `GCP_PROJECT` or `GOOGLE_CLOUD_PROJECT`. |
| `GCP_CREDENTIALS` | `object` | ADC | Explicit credentials object. Defaults to Application Default Credentials. |

### Azure Blob Storage

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AZURE_STORAGE_CONTAINER` | `str` | Env var | **Required.** Container name. |
| `AZURE_STORAGE_CONNECTION_STRING` | `str` | Env var | Connection string authentication. |
| `AZURE_STORAGE_ACCOUNT_URL` | `str` | Env var | Account URL for managed identity auth. |
| `AZURE_STORAGE_CREDENTIAL` | `object` | Auto | Explicit credential. Uses `DefaultAzureCredential` when not provided. |

### Engine Override

| Key | Type | Description |
|-----|------|-------------|
| `StorageEngine` | `Type[StorageEngine]` | Override the engine class for a specific field. |
| `storage_engine` | `StorageEngine` | Provide a pre-constructed engine instance. |
