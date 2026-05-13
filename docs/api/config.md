# Config

::: filestore.Config

A `TypedDict` with all optional keys. Accepted by `FileStore`, `FileField`, and all storage subclasses.

## General Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `destination` | `str \| Path \| callable` | CWD | Upload directory or cloud prefix |
| `filename` | `str \| Path \| callable` | Original name | Override stored filename |
| `filters` | `list[callable] \| callable` | `[]` | Filter callbacks |
| `metadata` | `dict \| callable` | `{}` | Extra per-file metadata |
| `extra_args` | `dict` | `{}` | Extra kwargs for backend upload call |

## Validation Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_file_size` | `int` | Unlimited | Maximum file size in bytes |
| `min_file_size` | `int` | `0` | Minimum file size in bytes |
| `allowed_extensions` | `list[str]` | All | Allowed file extensions (e.g. `[".jpg", ".png"]`) |
| `allowed_content_types` | `list[str]` | All | Allowed MIME types |

## Multipart Parsing Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_files` | `int` | `1000` | Max files in multipart body |
| `max_fields` | `int` | `1000` | Max fields in multipart body |
| `max_part_size` | `int` | `1048576` | Max part size in bytes |

## Local Storage Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `chunk_size` | `int` | `1048576` | Read/write chunk size |
| `overwrite` | `bool` | `False` | Allow overwriting existing files |
| `sanitize_filename` | `bool` | `True` | Replace unsafe filename characters |
| `base_url` | `str` | `None` | Public URL prefix |

## Cloud Keys

| Key | Type | Description |
|-----|------|-------------|
| `endpoint_url` | `str` | Custom endpoint for S3-compatible/emulator services |
| `AWS_BUCKET_NAME` | `str` | S3 bucket name |
| `AWS_DEFAULT_REGION` | `str` | AWS region |
| `GCP_BUCKET_NAME` | `str` | GCS bucket name |
| `GCP_PROJECT` | `str` | Google Cloud project ID |
| `GCP_CREDENTIALS` | `object` | Explicit GCS credentials |
| `AZURE_STORAGE_CONTAINER` | `str` | Azure container name |
| `AZURE_STORAGE_CONNECTION_STRING` | `str` | Azure connection string |
| `AZURE_STORAGE_ACCOUNT_URL` | `str` | Azure account URL |
| `AZURE_STORAGE_CREDENTIAL` | `object` | Explicit Azure credential |

## Usage

```python
from filestore import Config

config = Config(
    destination="uploads",
    max_file_size=5 * 1024 * 1024,
    allowed_extensions=[".jpg", ".png"],
)
```

Config is a `TypedDict`, so your IDE will provide autocompletion for all keys.
