# FileData

::: filestore.FileData

Per-file upload result returned by storage engines.

## Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `field_name` | `str` | Form field this file was submitted under |
| `filename` | `str \| None` | Final stored filename |
| `original_filename` | `str \| None` | Filename as submitted by the client |
| `path` | `Path \| None` | Absolute local path (local engine only) |
| `url` | `str \| None` | Public URL |
| `content_type` | `str \| None` | MIME type reported by client |
| `size` | `int \| None` | File size in bytes |
| `file` | `bytes \| None` | Raw bytes (memory engine only) |
| `metadata` | `dict[str, Any]` | Per-file metadata |
| `status` | `bool` | `True` on success, `False` on failure |
| `error` | `str \| None` | Error message (when `status=False`) |
| `message` | `str \| None` | Status message |
| `storage` | `str \| None` | Backend name (`"local"`, `"memory"`, `"s3"`, etc.) |

## Properties

### `location`

Returns the most useful persisted location — prefers `url` over `path`.

```python
file_data.location  # url if set, else path, else None
```

## Methods

### `to_dict()`

Returns a JSON-serializable dictionary. `Path` objects are converted to strings, `bytes` are represented as `<N bytes>`.

```python
file_data.to_dict()
# {
#     "field_name": "avatar",
#     "filename": "photo.jpg",
#     "path": "/app/uploads/photo.jpg",
#     "size": 1048576,
#     "status": True,
#     ...
# }
```
