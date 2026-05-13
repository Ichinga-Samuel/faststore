# Storage Engines

::: filestore.StorageEngine

All storage backends extend `StorageEngine` and implement the `upload()` method.

## Base Class

```python
class StorageEngine(ABC):
    storage_name = "storage"
    default_chunk_size = 1024 * 1024  # 1 MiB

    def __init__(self, *, request: Request, form: FormData): ...

    @abstractmethod
    async def upload(self, file_field: FileField, file: UploadFile) -> FileData: ...
```

## Built-in Engines

| Engine | Storage Name | Module |
|--------|-------------|--------|
| `LocalEngine` | `"local"` | `filestore.storage_engines.local_engine` |
| `MemoryEngine` | `"memory"` | `filestore.storage_engines.memory_engine` |
| `S3Engine` | `"s3"` | `filestore.storage_engines.s3_engine` |
| `GCSEngine` | `"gcs"` | `filestore.storage_engines.gcs_engine` |
| `AzureBlobEngine` | `"azure"` | `filestore.storage_engines.azure_engine` |

## Custom Engine

Create your own storage backend:

```python
from filestore import FileData, FileField, StorageEngine
from starlette.datastructures import UploadFile


class RedisEngine(StorageEngine):
    storage_name = "redis"

    async def upload(self, file_field: FileField, file: UploadFile) -> FileData:
        data = await file.read()
        key = f"uploads:{file.filename}"
        # await redis.set(key, data)

        return FileData(
            field_name=file_field.name,
            filename=file.filename,
            content_type=file.content_type,
            size=len(data),
            url=f"redis://{key}",
            status=True,
            storage=self.storage_name,
        )
```

Use it:

```python
from filestore import FileStore

storage = FileStore(name="file")
storage.StorageEngine = RedisEngine
```

## Helper Methods

All engines inherit these from `StorageEngine`:

| Method | Description |
|--------|-------------|
| `resolve_destination()` | Resolve destination from config (supports callables) |
| `get_chunk_size()` | Get chunk size from config with fallback |
| `get_size_hint()` | Get reported file size |
| `detect_stream_size()` | Measure stream size without consuming it |
| `validate_size_limits()` | Check size against min/max config |
