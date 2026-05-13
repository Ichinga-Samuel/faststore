# FileField

::: filestore.FileField

Declarative definition of an upload field.

## Constructor

```python
FileField(
    name: str,
    max_count: int = 1,
    required: bool = False,
    config: Config | dict = {},
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | **Required** | HTML form field name |
| `max_count` | `int` | `1` | Max files accepted for this field |
| `required` | `bool` | `False` | Fail if no files submitted |
| `config` | `Config \| dict` | `{}` | Per-field config (overrides store config) |

## Validation

- `name` must not be empty
- `max_count` must be ≥ 1
- `config` is copied on construction (mutations don't affect the original)

```python
from filestore import FileField

# Valid
field = FileField(name="avatar", max_count=3, required=True)

# Raises ValueError
field = FileField(name="")          # empty name
field = FileField(name="f", max_count=0)  # count < 1
```

## Usage

```python
from filestore import Config, FileField, FileStore

storage = FileStore(
    fields=[
        FileField(
            name="avatar",
            required=True,
            config=Config(
                allowed_extensions=[".jpg", ".png"],
                max_file_size=2 * 1024 * 1024,
            ),
        ),
        FileField(name="resume", max_count=3),
    ],
)
```
