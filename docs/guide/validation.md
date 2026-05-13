# Validation

Faststore validates every upload before persisting it. Validation failures are captured per-file in the `Store` result — they don't crash your endpoint.

## File Size Limits

```python
from filestore import Config, LocalStorage

storage = LocalStorage(
    name="document",
    config=Config(
        destination="uploads",
        max_file_size=10 * 1024 * 1024,  # 10 MB
        min_file_size=1,                  # At least 1 byte (reject empty files)
    ),
)
```

!!! tip "Streaming validation"
    For `LocalStorage`, size limits are checked **during** the write — not after. If a file exceeds `max_file_size` mid-stream, the write is aborted immediately and the temp file is cleaned up.

## Extension Allow-List

```python
config = Config(
    allowed_extensions=[".jpg", ".jpeg", ".png", ".webp"],
)
```

Extensions are case-insensitive. The leading dot is optional — `"png"` and `".png"` are both accepted.

You can also pass a single string:

```python
config = Config(allowed_extensions=".pdf")
```

## Content-Type Allow-List

```python
config = Config(
    allowed_content_types=["image/jpeg", "image/png", "image/webp"],
)
```

!!! warning "Client-reported types"
    The content type comes from the client's `Content-Type` header. It is **not** verified against the actual file content. For security-critical validation, combine this with a [custom filter](#custom-filters).

## Custom Filters

For validation logic that goes beyond size and type, use filter callbacks:

```python
from filestore import Config, MemoryStorage


async def no_executables(request, form, field_name, file):
    """Reject files with dangerous extensions."""
    dangerous = {".exe", ".bat", ".cmd", ".sh", ".ps1"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if f".{ext}" in dangerous:
        return f"Executable files are not allowed: {file.filename}"
    return True


storage = MemoryStorage(
    name="file",
    config=Config(filters=[no_executables]),
)
```

### Filter Return Values

| Return Value | Effect |
|-------------|--------|
| `True` | Accept the file, continue to next filter |
| `False` | Reject the file with a generic message |
| `"Custom message"` | Reject the file with the given message |

### Multiple Filters

Filters run in order. The first rejection stops the chain:

```python
config = Config(
    filters=[
        check_file_magic,     # Run first
        check_virus_scan,     # Run second (only if first passed)
        check_content_policy,  # Run third
    ],
)
```

### Sync and Async

Filters can be sync or async — faststore handles both:

```python
# Sync filter
def check_size(request, form, field_name, file):
    return True

# Async filter
async def check_virus(request, form, field_name, file):
    result = await virus_scanner.scan(file)
    return result.is_clean or "File failed virus scan"
```

## Combining Validation

All validation types work together:

```python
config = Config(
    destination="uploads/images",
    allowed_extensions=[".jpg", ".png"],
    allowed_content_types=["image/jpeg", "image/png"],
    max_file_size=5 * 1024 * 1024,
    min_file_size=100,
    filters=[custom_image_validator],
)
```

Validation runs in this order:

1. **Extension check** — based on the resolved filename
2. **Content-type check** — based on the client-reported MIME type
3. **Size check** (pre-upload) — based on the `Content-Length` hint
4. **Custom filters** — your callbacks
5. **Size check** (post-upload) — verified against actual bytes written

## Handling Validation Failures

Failed files don't raise exceptions. They appear in the `Store` result:

```python
@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    if not store.status:
        return {"errors": store.errors}

    for file_data in store.failed_files:
        print(f"Rejected: {file_data.original_filename} — {file_data.error}")

    for file_data in store.successful_files:
        print(f"Saved: {file_data.filename} ({file_data.size} bytes)")
```
