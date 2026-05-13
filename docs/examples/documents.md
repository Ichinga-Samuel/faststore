# Document Upload Service

A multi-file document upload endpoint using S3 storage with metadata tracking.

## Full Example

```python title="app.py"
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from filestore import Config, FileField, S3Storage, Store

app = FastAPI()


def document_metadata(request, form, field_name, file):
    """Attach request context as metadata."""
    return {
        "uploaded_by": request.headers.get("X-User-ID", "anonymous"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "original_name": file.filename,
        "ip": request.client.host if request.client else None,
    }


storage = S3Storage(
    fields=[
        FileField(
            name="documents",
            required=True,
            max_count=10,
            config=Config(
                destination="uploads/documents",
                allowed_extensions=[".pdf", ".docx", ".xlsx", ".pptx", ".txt"],
                max_file_size=50 * 1024 * 1024,  # 50 MB per file
            ),
        ),
    ],
    config=Config(
        AWS_BUCKET_NAME="my-documents-bucket",
        AWS_DEFAULT_REGION="us-east-1",
        metadata=document_metadata,
    ),
)


@app.post("/documents")
async def upload_documents(store: Store = Depends(storage)):
    return {
        "status": store.status,
        "uploaded": [
            {
                "filename": f.filename,
                "url": f.url,
                "size": f.size,
                "metadata": f.metadata,
            }
            for f in store.successful_files
        ],
        "rejected": [
            {
                "filename": f.original_filename,
                "error": f.error,
            }
            for f in store.failed_files
        ],
        "total_size_mb": round(store.total_size / (1024 * 1024), 2),
    }
```

## Key Points

- **Up to 10 files** per request with `max_count=10`
- **50 MB per file** limit
- **Metadata callback** captures upload context for audit trails
- **Structured response** separates successes from failures
- **`total_size`** for aggregate reporting
