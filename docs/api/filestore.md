# FileStore

::: filestore.FileStore

The core orchestration class. Used as a FastAPI dependency.

## Constructor

```python
FileStore(
    name: str | None = None,
    count: int = 1,
    required: bool = False,
    fields: list[FileField] | None = None,
    config: Config | Mapping[str, Any] | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str \| None` | `None` | Shorthand for defining a single field |
| `count` | `int` | `1` | Maximum file count (single-field shorthand) |
| `required` | `bool` | `False` | Whether the field is required |
| `fields` | `list[FileField] \| None` | `None` | Explicit list of field definitions |
| `config` | `Config \| dict \| None` | `None` | Store-level configuration |

## Usage

### Single Field

```python
from filestore import FileStore

storage = FileStore(name="avatar", count=1, required=True)
```

### Multiple Fields

```python
from filestore import FileField, FileStore

storage = FileStore(
    fields=[
        FileField(name="avatar", required=True),
        FileField(name="resume"),
    ],
)
```

### As a FastAPI Dependency

```python
from fastapi import Depends
from filestore import Store

@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    return store.to_dict()
```

## Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `fields` | `list[FileField]` | Configured upload fields |
| `config` | `dict[str, Any]` | Store-level configuration |
| `StorageEngine` | `Type[StorageEngine]` | Default engine class (`LocalEngine`) |

## Subclasses

| Class | Backend | Extra |
|-------|---------|-------|
| `LocalStorage` | Local filesystem | — |
| `MemoryStorage` | In-memory bytes | — |
| `S3Storage` | Amazon S3 | `filestore[s3]` |
| `GCSStorage` | Google Cloud Storage | `filestore[gcp]` |
| `AzureStorage` | Azure Blob Storage | `filestore[azure]` |
