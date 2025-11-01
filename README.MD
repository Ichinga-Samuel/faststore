# Filestore

[![PyPI version](https://badge.fury.io/py/filestore.svg)](https://badge.fury.io/py/filestore)
[![Python Versions](https://img.shields.io/pypi/pyversions/filestore.svg)](https://pypi.org/project/filestore)

A file storage package for FastAPI using its dependency injection mechanism, heavily inspired by [Multer](https://github.com/expressjs/multer) for Node.js.

`filestore` handles `multipart/form-data` uploads with ease. It provides a simple class-based dependency
that processes file uploads, saves them to a configurable storage backend, and returns a structured response.

---

## Features

* **Simple Dependency:** Integrates directly with FastAPI's `Depends` system.
* **Pluggable Storage:** Includes built-in storage engines for:
    * **Local** (`LocalStorage`): Save files to the local filesystem.
    * **In-Memory** (`MemoryStorage`): Hold file bytes in memory (available on the response object).
    * **Amazon S3** (`S3Storage`): Upload files directly to an S3 bucket.
* **Flexible Configuration:**
    * Handle single or multiple files from a single form field.
    * Handle files from multiple, different form fields.
    * Apply global and per-field configurations.
* **Dynamic & Async:**
    * Use **callables** for dynamic destinations or filenames (e.g., save to a user-specific folder).
    * Fully `async` support.
* **File Filtering:** Provide a list of callables to filter files before uploading (e.g., check MIME type).
* **Standardized Response:** Returns a clean `Store` object containing a list of `FileData` objects for all processed files.

---

## Installation

Install the basic package:

```bash
pip install filestore
````

To use S3 storage, you must also install `boto3`. You can do this with the `s3` extra:

```bash
pip install filestore[s3]
```

-----

## 🚀 Quick Start

Here is a complete example of uploading a single file named `file` to a local directory called `uploads/`.

```python
import uvicorn
from fastapi import FastAPI, Depends
from filestore import LocalStorage, Store

app = FastAPI()

# 1. Define the storage dependency
# This will accept a form field named "file" and allow a max of 1 file.
# Files will be saved in the "./uploads" directory.
storage = LocalStorage(
    name="file", 
    count=1, 
    required=True, 
    config={"destination": "uploads/"}
)

@app.post("/upload/")
async def upload_single_file(file_store: Store = Depends(storage)):
    """
    Upload a single file to local storage.
    
    The 'file_store' dependency handles everything.
    """
    if file_store.status:
        return {
            "message": "File uploaded successfully",
            "data": file_store.files
        }
    else:
        return {
            "message": "Upload failed", 
            "error": file_store.error
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

To test this, you can use `curl`:

```bash
curl -X POST "http://localhost:8000/upload/" -F "file=@/path/to/your/image.jpg"
```

### The Response Object

The `file_store` object returned by the dependency is an instance of `Store`.

  * **`store.status`** (bool): `True` if all uploads were successful, `False` otherwise.
  * **`store.files`** (dict): A dictionary where keys are the form **field names** and values are a **list** of `FileData` objects.
  * **`store.error`** (str): An error message, if any.
  * **`store.message`** (str): A response message

The `FileData` object contains metadata about the uploaded file:

  * `field_name`: The name of the form field (e.g., "file").
  * `filename`: The original name of the file (e.g., "image.jpg").
  * `path`: The *absolute* path where the file was saved (for `LocalStorage`).
  * `url`: The public URL of the file (for `S3Storage`).
  * `file`: The raw `bytes` of the file (for `MemoryStorage`).
  * `size`: The file size in bytes.
  * `content_type`: The file's MIME type.
  * `status`: `True` if this *specific* file was uploaded successfully.
  * `error`: An error message for this specific file.
  * `message`: A success message

-----

## Usage Examples

### 1\. Multiple Files (Single Field)

To accept multiple files from the *same* field (e.g., `name="images"`), just change the `count` parameter.

```python
from filestore import LocalStorage

# Accepts up to 10 files from the "gallery_images" field
gallery_storage = LocalStorage(
    name="gallery_images", 
    count=10, 
    config={"destination": "uploads/gallery"}
)

@app.post("/upload-gallery/")
async def upload_gallery(file_store: Store = Depends(gallery_storage)):
    # file_store.files["gallery_images"] will be a list of FileData objects
    return file_store
```

### 2\. Multiple *Different* Fields

To handle uploads from different form fields (e.g., an "avatar" and a "resume"), use the base `FileStore` class and pass a list of `FileField` objects.

```python
from filestore import FileStore, FileField, Store

# Define configuration for multiple fields
multi_field_storage = FileStore(fields=[
    FileField(
        name="avatar", 
        max_count=1, 
        required=True,
        config={"destination": "uploads/avatars"}
    ),
    FileField(
        name="resume", 
        max_count=1, 
        required=False,
        config={"destination": "uploads/resumes"}
    )
])

@app.post("/upload-profile/")
async def upload_profile(file_store: Store = Depends(multi_field_storage)):
    # Results are keyed by field name
    # file_store.files["avatar"] -> list[FileData]
    # file_store.files["resume"] -> list[FileData]
    return file_store
```

### 3\. In-Memory Storage

Use `MemoryStorage` to store the file as `bytes` in the `FileData.file` attribute instead of saving it to disk. This is useful for small files or for processing files immediately (e.g., resizing an image).

```python
from filestore import MemoryStorage, Store

# No destination needed
mem_storage = MemoryStorage(name="profile_pic", count=1)

@app.post("/upload-memory/")
async def upload_to_memory(file_store: Store = Depends(mem_storage)):
    if file_store.status:
        # Get the first (and only) file from the "profile_pic" field
        file_data = file_store.files["profile_pic"][0]
        
        # Access the file bytes directly
        file_bytes = file_data.file
        
        return {
            "message": "File processed in memory",
            "filename": file_data.filename,
            "size": file_data.size,
            "content_type": file_data.content_type
        }
    return file_store
```

### 4\. S3 Storage

Use `S3Storage` and provide S3-specific configuration. Assumes AWS credentials (key, secret) are available in your environment (e.g., via `~/.aws/credentials` or environment variables).

```python
from filestore import S3Storage, Store, Config

# Define the S3 config
s3_config = Config(
    destination="user-uploads/",  # Path/prefix within the bucket
    AWS_BUCKET_NAME="my-awesome-bucket",
    AWS_DEFAULT_REGION="us-east-1"
    # You can add 'extra_args' for S3, e.g.,
    # extra_args={"ACL": "public-read"}
)

s3_storage = S3Storage(name="document", config=s3_config)

@app.post("/upload-s3/")
async def upload_to_s3(file_store: Store = Depends(s3_storage)):
    # The 'url' attribute will be populated with the S3 file URL
    return file_store
```

-----

## Advanced Configuration

The `config` dictionary (and `FileField.config`) accepts callables for dynamic processing.

### 1\. Dynamic Destination Path

You can provide a callable to the `destination` config. The callable receives the `Request`, `FormData`, field name, and `UploadFile` object.

```python
from pathlib import Path
from starlette.requests import Request
from starlette.datastructures import FormData, UploadFile
from filestore import LocalStorage, Config

def get_user_upload_path(
    request: Request, 
    form: FormData, 
    field_name: str, 
    file: UploadFile
) -> Path:
    """Saves file to a user-specific folder, e.g., 'uploads/user_123/'"""
    user_id = request.headers.get("X-User-ID", "anonymous")
    return Path(f"uploads/users/{user_id}")

# Pass the function as the destination
dynamic_storage = LocalStorage(
    name="user_file",
    config=Config(destination=get_user_upload_path)
)

@app.post("/upload-dynamic-path/")
async def upload_dynamic_path(file_store: Store = Depends(dynamic_storage)):
    return file_store
```

### 2\. File Filtering

Provide a list of `filters`. Each filter is a callable that receives the request context and file, and returns `True` to *keep* the file or `False` to *reject* it.

```python
def check_is_image(
    request: Request, 
    form: FormData, 
    field_name: str, 
    file: UploadFile
) -> bool:
    """Only allow JPEG or PNG files."""
    return file.content_type in ["image/jpeg", "image/png"]

image_storage = LocalStorage(
    name="image",
    config=Config(
        destination="uploads/images_only",
        filters=[check_is_image] # Add the filter
    )
)

@app.post("/upload-image-only/")
async def upload_image_only(file_store: Store = Depends(image_storage)):
    # Files that fail the filter will not be in the response
    return file_store
```

### 3\. Dynamic Filename

You can also provide a `filename` callable. This is useful for sanitizing filenames or ensuring uniqueness.

**Note:** The `filename` callable should return an `UploadFile` object (or an object with a `.filename` attribute).
*This function does not rename the file on disk*, but rather changes the `filename` attribute of the `UploadFile` object
before it is passed to the storage engine.

```python
import uuid

def unique_filename(
    request: Request, 
    form: FormData, 
    field_name: str, 
    file: UploadFile
) -> UploadFile:
    """Renames the file to a unique UUID."""
    ext = Path(file.filename).suffix
    file.filename = f"{uuid.uuid4()}{ext}"
    return file

rename_storage = LocalStorage(
    name="data",
    config=Config(
        destination="uploads/data",
        filename=unique_filename # Add the filename callable
    )
)

@app.post("/upload-renamed/")
async def upload_renamed(file_store: Store = Depends(rename_storage)):
    # The 'filename' in the FileData response will be the new UUID
    return file_store
```
