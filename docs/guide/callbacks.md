# Callbacks

Faststore supports dynamic resolution of filenames, destinations, metadata, and filters via callbacks. Every callback receives the same four arguments:

```python
def callback(request, form, field_name, file):
    ...
```

| Argument | Type | Description |
|----------|------|-------------|
| `request` | `Request` | The Starlette/FastAPI request object |
| `form` | `FormData` | The parsed multipart form data |
| `field_name` | `str` | Name of the upload field being processed |
| `file` | `UploadFile` | The file being processed |

All callbacks can be **sync or async** — faststore handles both transparently.

---

## Dynamic Destination

Route uploads to different directories based on request context:

```python
from pathlib import Path
from filestore import Config, LocalStorage


async def user_directory(request, form, field_name, file):
    """Store uploads in per-user directories."""
    user_id = request.headers.get("X-User-ID", "anonymous")
    return Path("uploads") / user_id


storage = LocalStorage(
    name="file",
    config=Config(destination=user_directory),
)
```

For cloud backends, the destination becomes the key prefix:

```python
async def tenant_prefix(request, form, field_name, file):
    tenant = request.headers.get("X-Tenant-ID")
    return f"tenants/{tenant}/uploads"

storage = S3Storage(
    name="file",
    config=Config(
        destination=tenant_prefix,
        AWS_BUCKET_NAME="my-bucket",
    ),
)
```

---

## Dynamic Filename

Override the stored filename:

```python
import uuid
from pathlib import Path
from filestore import Config, LocalStorage


def unique_name(request, form, field_name, file):
    """Generate a UUID-based filename, preserving the extension."""
    suffix = Path(file.filename or "").suffix
    return f"{uuid.uuid4()}{suffix}"


storage = LocalStorage(
    name="file",
    config=Config(destination="uploads", filename=unique_name),
)
```

### Subdirectory in Filename

The callback can return a path with subdirectories:

```python
from datetime import date

def dated_name(request, form, field_name, file):
    today = date.today().isoformat()
    return f"{today}/{file.filename}"
```

This creates `uploads/2026-05-13/report.pdf`.

### Returning an UploadFile

For advanced use, the filename callback can return a modified `UploadFile`:

```python
def rename_file(request, form, field_name, file):
    file.filename = "renamed.txt"
    return file
```

### Static Filename

You can also set a fixed string instead of a callback:

```python
config = Config(filename="data.csv")
```

---

## Metadata Callbacks

Attach custom metadata to each uploaded file:

```python
from filestore import Config, LocalStorage


def request_metadata(request, form, field_name, file):
    return {
        "request_id": request.headers.get("X-Request-ID"),
        "uploaded_by": request.headers.get("X-User-ID"),
        "ip_address": request.client.host if request.client else None,
    }


storage = LocalStorage(
    name="file",
    config=Config(destination="uploads", metadata=request_metadata),
)
```

The returned dict is merged into `FileData.metadata`:

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    file_data = store.first("file")
    print(file_data.metadata)
    # {"relative_path": "report.pdf", "request_id": "abc-123", ...}
```

### Static Metadata

Pass a dict directly for fixed metadata:

```python
config = Config(metadata={"source": "web-upload"})
```

---

## Filter Callbacks

See the [Validation guide](validation.md#custom-filters) for full details on filter callbacks.

---

## Async Callbacks

All callbacks support async:

```python
async def resolve_destination(request, form, field_name, file):
    user = await get_current_user(request)
    return f"uploads/{user.id}"

async def resolve_filename(request, form, field_name, file):
    hash = await compute_hash(file)
    return f"{hash}{Path(file.filename).suffix}"

async def resolve_metadata(request, form, field_name, file):
    return {"processed_at": datetime.utcnow().isoformat()}
```

---

## Per-Field Callbacks

Callbacks can be set at the store level (applies to all fields) or per-field (overrides the store level):

```python
from filestore import Config, FileField, FileStore

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            config=Config(
                destination="uploads/avatars",
                filename=avatar_namer,  # Only for avatars
            ),
        ),
        FileField(
            name="document",
            config=Config(
                destination="uploads/docs",
                filename=document_namer,  # Only for documents
            ),
        ),
    ],
    config=Config(
        metadata=shared_metadata,  # Applied to all fields
    ),
)
```
