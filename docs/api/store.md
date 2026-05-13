# Store

::: filestore.Store

Aggregated response for all processed upload fields. This is the object returned by the FastAPI dependency.

## Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `files` | `dict[str, list[FileData]]` | Per-field file results |
| `status` | `bool` | `True` when all files succeeded |
| `error` | `str \| None` | First error message |
| `message` | `str \| None` | Summary status message |
| `errors` | `list[str]` | All error messages |
| `messages` | `list[str]` | All informational messages |

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `flat_files` | `list[FileData]` | All files in a single list |
| `successful_files` | `list[FileData]` | Only files with `status=True` |
| `failed_files` | `list[FileData]` | Only files with `status=False` |
| `total_files` | `int` | Total file count |
| `total_size` | `int` | Sum of sizes for successful files |

## Methods

### `first(field_name)`

```python
store.first("avatar")  # FileData | None
```

### `add(file_data)`

```python
store.add(file_data)  # Append a FileData to the store
```

### `to_dict()`

```python
store.to_dict()  # JSON-serializable dict
```
