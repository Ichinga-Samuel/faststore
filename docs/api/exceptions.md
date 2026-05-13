# Exceptions

::: filestore.exceptions

All exceptions inherit from `FileStoreError`.

## Hierarchy

| Exception | Parent | Raised When |
|-----------|--------|-------------|
| `FileStoreError` | `Exception` | Base — catch to handle any filestore error |
| `ConfigurationError` | `FileStoreError` | Invalid config (duplicate fields, missing engine) |
| `ValidationError` | `FileStoreError` | File fails size validation |
| `StorageError` | `FileStoreError` | Backend cannot persist a file |
| `MissingDependencyError` | `FileStoreError` | Cloud SDK not installed |

## Usage

```python
from filestore import FileStoreError, ConfigurationError

# Catch all filestore errors
try:
    storage = LocalStorage(name="file", config=bad_config)
except FileStoreError as err:
    print(f"Filestore error: {err}")

# Catch specific errors
try:
    from filestore import S3Storage
    storage = S3Storage(name="file")
except MissingDependencyError:
    print("Install filestore[s3]")
```

!!! note
    Validation failures during upload do **not** raise exceptions. They are captured in `FileData.error` and `Store.errors`.
