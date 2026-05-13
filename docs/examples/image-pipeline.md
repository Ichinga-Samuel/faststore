# Image Processing Pipeline

Use `MemoryStorage` to receive images in memory and process them without touching the filesystem.

## Full Example

```python title="app.py"
import hashlib
from io import BytesIO

from fastapi import Depends, FastAPI
from fastapi.responses import Response
from filestore import Config, MemoryStorage, Store

app = FastAPI()


async def image_filter(request, form, field_name, file):
    """Verify the file starts with a known image magic number."""
    await file.seek(0)
    header = await file.read(8)
    await file.seek(0)

    png_magic = b"\x89PNG\r\n\x1a\n"
    jpeg_magic = b"\xff\xd8\xff"

    if header.startswith(png_magic) or header.startswith(jpeg_magic):
        return True
    return "File does not appear to be a valid PNG or JPEG image"


storage = MemoryStorage(
    name="image",
    required=True,
    config=Config(
        allowed_content_types=["image/jpeg", "image/png"],
        max_file_size=10 * 1024 * 1024,  # 10 MB
        filters=[image_filter],
    ),
)


@app.post("/images/process")
async def process_image(store: Store = Depends(storage)):
    image = store.first("image")

    if not image or not image.status:
        return {"error": store.error}

    raw_bytes = image.file  # bytes — the full image payload

    # Compute a content hash
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    return {
        "filename": image.original_filename,
        "content_type": image.content_type,
        "size": image.size,
        "sha256": content_hash,
    }
```

## Key Points

- **`MemoryStorage`** — no disk I/O, the full payload is in `image.file`
- **Magic number filter** — validates actual file content, not just headers
- **Content hashing** — process bytes directly in-memory
- Useful for **thumbnailing**, **OCR**, **virus scanning**, or **forwarding** to another service
