# Installation

## Base Package

Install **faststore** with pip:

```bash
pip install filestore
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add filestore
```

The base install includes the **local filesystem** and **in-memory** storage backends with no additional dependencies beyond FastAPI itself.

## Cloud Storage Extras

Cloud backends are installed as optional extras so the base package stays lean.

=== "Amazon S3"

    ```bash
    pip install "filestore[s3]"
    ```

    Installs [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) for S3 and S3-compatible services (MinIO, LocalStack, etc.).

=== "Google Cloud Storage"

    ```bash
    pip install "filestore[gcp]"
    ```

    Installs [`google-cloud-storage`](https://cloud.google.com/python/docs/reference/storage/latest) for GCS.

=== "Azure Blob Storage"

    ```bash
    pip install "filestore[azure]"
    ```

    Installs [`azure-storage-blob`](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/) and [`azure-identity`](https://learn.microsoft.com/en-us/python/api/azure-identity/) for Azure Blob Storage.

## Optional Extras

=== "Pydantic Models"

    ```bash
    pip install "filestore[pydantic]"
    ```

    Enables the `FileModel()` helper that generates a Pydantic model from your upload field definitions.

## Multiple Extras

Install multiple extras at once:

```bash
pip install "filestore[s3,gcp,azure]"
```

## Requirements

- **Python** ≥ 3.11
- **FastAPI** ≥ 0.120.0

## Verify Installation

```python
import filestore
print(filestore.__version__)
```
