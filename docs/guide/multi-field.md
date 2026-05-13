# Multi-Field Uploads

Faststore supports handling multiple upload fields in a single request, each with its own configuration and validation rules.

## Defining Multiple Fields

Use `FileField` to declare each upload field:

```python
from filestore import Config, FileField, FileStore

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            required=True,
            max_count=1,
            config=Config(
                destination="uploads/avatars",
                allowed_extensions=[".jpg", ".png"],
                max_file_size=2 * 1024 * 1024,
            ),
        ),
        FileField(
            name="documents",
            required=False,
            max_count=5,
            config=Config(
                destination="uploads/docs",
                allowed_extensions=[".pdf", ".docx"],
                max_file_size=10 * 1024 * 1024,
            ),
        ),
    ],
)
```

### Using with a Backend

To use a specific backend with multi-field, set the `StorageEngine` class attribute or use a storage subclass:

```python
from filestore import FileField, MemoryStorage

# Option 1: Use a storage subclass
storage = MemoryStorage(
    fields=[
        FileField(name="avatar", required=True),
        FileField(name="resume"),
    ],
)
```

```python
from filestore import FileField, FileStore, MemoryEngine

# Option 2: Set the engine class
storage = FileStore(
    fields=[
        FileField(name="avatar", required=True),
        FileField(name="resume"),
    ],
)
storage.StorageEngine = MemoryEngine
```

## Reading Multi-Field Results

```python
@app.post("/profile")
async def update_profile(store: Store = Depends(storage)):
    # Access files by field name
    avatar = store.first("avatar")
    documents = store.files.get("documents", [])

    return {
        "avatar": avatar.filename if avatar else None,
        "documents": [doc.filename for doc in documents if doc.status],
        "status": store.status,
        "errors": store.errors,
    }
```

## Config Inheritance

Per-field config overrides the store-level config. Filters are **concatenated** (both run):

```python
def global_size_check(request, form, field_name, file):
    return True

def avatar_dimension_check(request, form, field_name, file):
    return True

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            config=Config(filters=[avatar_dimension_check]),  # (1)!
        ),
    ],
    config=Config(filters=[global_size_check]),  # (2)!
)
```

1. This filter runs **after** the global filter.
2. This filter runs first for **all** fields.

Both `global_size_check` and `avatar_dimension_check` will run for the `avatar` field.

## Max Count Enforcement

When more files are submitted than `max_count` allows, the extras are rejected:

```python
field = FileField(name="photos", max_count=3)
# If 5 photos are submitted, 3 are processed and 2 are rejected
```

Rejected files appear in `store.failed_files` with a clear error message.

## Mixed Backends

For advanced use, different fields can use different storage engines via per-field config:

```python
from filestore import Config, FileField, FileStore, LocalEngine, MemoryEngine

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            config=Config(
                StorageEngine=LocalEngine,
                destination="uploads/avatars",
            ),
        ),
        FileField(
            name="thumbnail",
            config=Config(
                StorageEngine=MemoryEngine,  # Keep in memory for processing
            ),
        ),
    ],
)
```
