"""Exception hierarchy for the filestore package.

All exceptions inherit from :class:`FileStoreError` so callers can catch
the entire family with a single handler when appropriate.
"""

from __future__ import annotations


class FileStoreError(Exception):
    """Base exception for all filestore errors."""


class ConfigurationError(FileStoreError):
    """Raised when the store or a field is configured incorrectly."""


class ValidationError(FileStoreError):
    """Raised when an uploaded file fails a validation check."""


class StorageError(FileStoreError):
    """Raised when a storage backend cannot persist an upload."""


class MissingDependencyError(FileStoreError):
    """Raised when an optional backend dependency is not installed."""
