# User Avatars

A complete example of handling user avatar uploads with image validation, UUID filenames, and per-user directories.

## Full Example

```python title="app.py"
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from filestore import Config, LocalStorage, Store

app = FastAPI()


def avatar_filename(request, form, field_name, file):
    """Generate a UUID filename preserving the original extension."""
    ext = Path(file.filename or "").suffix.lower()
    return f"{uuid.uuid4()}{ext}"


async def user_directory(request, form, field_name, file):
    """Route uploads to per-user directories."""
    user_id = request.headers.get("X-User-ID", "default")
    return Path("uploads/avatars") / user_id


storage = LocalStorage(
    name="avatar",
    required=True,
    config=Config(
        destination=user_directory,
        filename=avatar_filename,
        base_url="/media/avatars",
        allowed_extensions=[".jpg", ".jpeg", ".png", ".webp"],
        allowed_content_types=[
            "image/jpeg",
            "image/png",
            "image/webp",
        ],
        max_file_size=2 * 1024 * 1024,  # 2 MB
        overwrite=True,  # Replace existing avatar
    ),
)


@app.post("/users/avatar")
async def upload_avatar(store: Store = Depends(storage)):
    if not store.status:
        raise HTTPException(status_code=422, detail=store.errors)

    avatar = store.first("avatar")
    return {
        "url": avatar.url,
        "size": avatar.size,
        "content_type": avatar.content_type,
    }
```

## Key Points

- **UUID filenames** prevent collisions and information leakage
- **Per-user directories** keep uploads organized
- **Extension + content-type** validation for defense in depth
- **2 MB limit** prevents abuse
- **`overwrite=True`** replaces the old avatar automatically
