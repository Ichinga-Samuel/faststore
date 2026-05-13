# Quick Start

This guide walks you through building your first file upload endpoint with **filestore**.

## 1. Create a FastAPI App

```python title="app.py"
from fastapi import Depends, FastAPI
from filestore import LocalStorage, Store

app = FastAPI()

# Configure a storage instance
storage = LocalStorage(
    name="file",          # HTML form field name
    required=True,        # Reject requests with no files
    config={
        "destination": "uploads",     # Directory to write files to
        "base_url": "/media",         # Public URL prefix
    },
)


@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    """Accept a single file upload."""
    file_data = store.first("file")
    return {
        "status": store.status,
        "filename": file_data.filename,
        "path": str(file_data.path),
        "url": file_data.url,
        "size": file_data.size,
    }
```

## 2. Run It

```bash
uvicorn app:app --reload
```

## 3. Test It

=== "curl"

    ```bash
    curl -X POST http://localhost:8000/upload \
      -F "file=@document.pdf"
    ```

=== "httpx (Python)"

    ```python
    import httpx

    with open("document.pdf", "rb") as f:
        response = httpx.post(
            "http://localhost:8000/upload",
            files={"file": ("document.pdf", f, "application/pdf")},
        )
    print(response.json())
    ```

=== "JavaScript (fetch)"

    ```javascript
    const form = new FormData();
    form.append("file", fileInput.files[0]);

    const response = await fetch("/upload", {
      method: "POST",
      body: form,
    });
    const data = await response.json();
    ```

## What Happened?

1. FastAPI parsed the multipart request and extracted the `file` field
2. **filestore** validated the upload (size, type, etc.)
3. The file was written atomically to `uploads/document.pdf`
4. If `document.pdf` already existed, it was automatically renamed to `document-1.pdf`
5. A `Store` object was returned with all the results

## Adding Validation

Let's restrict uploads to images under 5 MB:

```python title="app.py"
from filestore import Config, LocalStorage

storage = LocalStorage(
    name="image",
    required=True,
    config=Config(
        destination="uploads/images",
        base_url="/media/images",
        allowed_extensions=[".jpg", ".jpeg", ".png", ".webp"],
        allowed_content_types=["image/jpeg", "image/png", "image/webp"],
        max_file_size=5 * 1024 * 1024,  # 5 MB
    ),
)
```

Now any file that doesn't match the constraints will be rejected with a clear error message in `store.errors`.

## Switching Backends

The beauty of filestore is that **every backend shares the same API**. To switch from local to S3:

```python
# Before: local storage
from filestore import LocalStorage
storage = LocalStorage(name="file", config={"destination": "uploads"})

# After: S3 storage
from filestore import S3Storage
storage = S3Storage(
    name="file",
    config={
        "destination": "uploads",
        "AWS_BUCKET_NAME": "my-bucket",
        "AWS_DEFAULT_REGION": "us-east-1",
    },
)
```

Your endpoint code doesn't change at all.

## Next Steps

- **[Storage Backends](../guide/backends.md)** — Learn about all five backends in detail
- **[Validation](../guide/validation.md)** — File size, extensions, content types, and custom filters
- **[Callbacks](../guide/callbacks.md)** — Dynamic filenames, destinations, and metadata
- **[Multi-Field Uploads](../guide/multi-field.md)** — Handle multiple upload fields per request
