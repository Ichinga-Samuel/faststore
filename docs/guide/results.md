# Reading Results

Every upload request returns a `Store` object with structured results for all processed fields and files.

## The Store Object

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    store.status           # True if ALL files succeeded
    store.message          # Summary message
    store.error            # First error (if any)
    store.files            # dict[str, list[FileData]]
    store.flat_files       # All files in one list
    store.successful_files # Only successes
    store.failed_files     # Only failures
    store.total_files      # Count of all files
    store.total_size       # Sum of sizes for successful files
    store.first("avatar")  # First FileData for "avatar", or None
    store.errors           # All error messages
    store.messages         # All informational messages
```

## The FileData Object

Each processed file produces a `FileData`:

```python
file_data = store.first("avatar")

# Identity
file_data.field_name         # "avatar"
file_data.filename           # "photo.jpg" (final stored name)
file_data.original_filename  # "IMG_2024.jpg" (as submitted)

# Location
file_data.path               # Path("/app/uploads/photo.jpg") — local only
file_data.url                # "/media/photo.jpg" — if base_url was set
file_data.location           # url or path (whichever is available)

# Content
file_data.content_type       # "image/jpeg"
file_data.size               # 1048576 (bytes)
file_data.file               # b"..." — memory engine only

# Status
file_data.status             # True / False
file_data.error              # Error message (when status=False)
file_data.message            # "photo.jpg uploaded successfully"
file_data.storage            # "local", "memory", "s3", "gcs", "azure"

# Extras
file_data.metadata           # {"relative_path": "photo.jpg", ...}
```

## Common Patterns

### Return All Files as JSON

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    return store.to_dict()
```

`to_dict()` is JSON-serializable — `Path` objects become strings, `bytes` become `<N bytes>`.

### Check Overall Status

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    if not store.status:
        raise HTTPException(status_code=400, detail=store.errors)
    return {"files": [f.filename for f in store.successful_files]}
```

### Process Each File

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    results = []
    for file_data in store.flat_files:
        if file_data.status:
            results.append({
                "name": file_data.filename,
                "url": file_data.url,
                "size": file_data.size,
            })
        else:
            results.append({
                "name": file_data.original_filename,
                "error": file_data.error,
            })
    return {"files": results}
```

### Access Memory Bytes

```python
from filestore import MemoryStorage

storage = MemoryStorage(name="image")

@app.post("/process")
async def process(store: Store = Depends(storage)):
    image = store.first("image")
    raw_bytes = image.file  # bytes
    # Process the image...
```

### Aggregate Size

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    return {
        "total_files": store.total_files,
        "total_size_mb": round(store.total_size / (1024 * 1024), 2),
        "successful": len(store.successful_files),
        "failed": len(store.failed_files),
    }
```
