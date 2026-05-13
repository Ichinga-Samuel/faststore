---
hide:
  - navigation
---

# Faststore

<div style="text-align: center; margin: 2rem 0;">
<p style="font-size: 1.4rem; color: var(--md-default-fg-color--light);">
Production-ready file upload toolkit for FastAPI
</p>
</div>

[![PyPI version](https://badge.fury.io/py/filestore.svg)](https://pypi.org/project/filestore)
[![Python Versions](https://img.shields.io/pypi/pyversions/filestore.svg)](https://pypi.org/project/filestore)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

**Faststore** is a small FastAPI upload library with a simple dependency-based API and production-grade defaults. It keeps the happy path short, but adds the things real services usually need.

## Features

<div class="grid cards" markdown>

-   :material-harddisk:{ .lg .middle } **Multiple Storage Backends**

    ---

    Local filesystem, in-memory, Amazon S3, Google Cloud Storage, and Azure Blob Storage — all with the same API.

-   :material-shield-check:{ .lg .middle } **Built-in Validation**

    ---

    Validate file size, extension, and content type out of the box. Add custom filter callbacks for application-specific rules.

-   :material-swap-horizontal:{ .lg .middle } **Sync & Async Callbacks**

    ---

    Dynamically resolve filenames, destinations, filters, and metadata with sync or async callables.

-   :material-file-multiple:{ .lg .middle } **Multi-Field Support**

    ---

    Handle multiple upload fields in a single request with per-field configuration and validation.

-   :material-puzzle:{ .lg .middle } **FastAPI Native**

    ---

    Works as a standard FastAPI dependency — just `Depends()` and go. No middleware, no magic.

-   :material-package-variant:{ .lg .middle } **Lean Install**

    ---

    Zero cloud SDK dependencies by default. Install only the extras you need: `filestore[s3]`, `filestore[gcp]`, `filestore[azure]`.

</div>

## Quick Example

```python
from fastapi import Depends, FastAPI
from filestore import LocalStorage, Store

app = FastAPI()

storage = LocalStorage(
    name="file",
    required=True,
    config={"destination": "uploads", "base_url": "/media"},
)


@app.post("/upload")
async def upload(store: Store = Depends(storage)):
    file_data = store.first("file")
    return {
        "status": store.status,
        "filename": file_data.filename,
        "url": file_data.url,
    }
```

That's it. Uploads are validated, written atomically to disk, and collision-free by default.

## Next Steps

<div class="grid cards" markdown>

-   [:material-download: **Installation**](getting-started/installation.md)

    Install faststore and optional cloud backends

-   [:material-rocket-launch: **Quick Start**](getting-started/quickstart.md)

    Build your first upload endpoint in 5 minutes

-   [:material-book-open-variant: **User Guide**](guide/index.md)

    Learn all the features in depth

-   [:material-code-tags: **API Reference**](api/index.md)

    Full reference for every class and function

</div>
