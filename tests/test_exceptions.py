"""Tests for filestore.exceptions — exception hierarchy."""

from __future__ import annotations

import pytest

from filestore import (
    ConfigurationError,
    FileStoreError,
    MissingDependencyError,
    StorageError,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        for exc_cls in [ConfigurationError, ValidationError, StorageError, MissingDependencyError]:
            assert issubclass(exc_cls, FileStoreError)
            assert issubclass(exc_cls, Exception)

    def test_base_catchable(self):
        with pytest.raises(FileStoreError):
            raise ConfigurationError("bad config")

    def test_validation_error(self):
        with pytest.raises(ValidationError, match="too big"):
            raise ValidationError("too big")

    def test_storage_error(self):
        with pytest.raises(StorageError, match="disk full"):
            raise StorageError("disk full")

    def test_missing_dependency(self):
        with pytest.raises(MissingDependencyError, match="install"):
            raise MissingDependencyError("install boto3")

    def test_configuration_error(self):
        with pytest.raises(ConfigurationError, match="duplicate"):
            raise ConfigurationError("duplicate fields")
