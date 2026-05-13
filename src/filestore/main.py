"""Core orchestration for processing multipart upload requests.

:class:`FileStore` is a FastAPI dependency that parses form data,
validates each file against its field constraints, and delegates
persistence to a pluggable :class:`~filestore.storage_engines.StorageEngine`.
"""

import asyncio
from dataclasses import dataclass, replace
from logging import getLogger
from typing import Any, Iterable, Mapping, Type

from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

from .datastructures import Config, FileData, FileField, Store
from .exceptions import ConfigurationError, FileStoreError, ValidationError
from .storage_engines import LocalEngine, StorageEngine
from .util import (
    dedupe,
    file_size_hint,
    maybe_await,
    normalize_callable_list,
    normalize_config,
    normalize_relative_filename,
)

logger = getLogger(__name__)


@dataclass(slots=True)
class PreparedUpload:
    """Internal object holding a validated upload ready for persistence.

    Attributes:
        file: The (possibly renamed) :class:`UploadFile`.
        original_filename: The filename as submitted by the client.
        metadata: Extra metadata resolved from callbacks.
    """

    file: UploadFile
    original_filename: str | None
    metadata: dict[str, Any]


class FileStore:
    """FastAPI dependency for storing uploaded files with pluggable backends.

    Can be used as a single-field shortcut::

        storage = FileStore(name="avatar", count=1, required=True)

    Or with multiple fields::

        storage = FileStore(fields=[
            FileField(name="avatar", required=True),
            FileField(name="resume", required=False),
        ])

    Use as a FastAPI dependency::

        @app.post("/upload")
        async def upload(store: Store = Depends(storage)):
            ...

    Args:
        name: Shorthand for defining a single field.
        count: Maximum file count for the single-field shorthand.
        required: Whether the single field is required.
        fields: Explicit list of :class:`FileField` definitions.
        config: Store-level configuration applied to all fields.
    """

    fields: list[FileField]
    config: dict[str, Any]
    StorageEngine: Type[StorageEngine] = LocalEngine

    def __init__(
        self,
        name: str | None = None,
        count: int = 1,
        required: bool = False,
        fields: list[FileField] | None = None,
        config: Config | Mapping[str, Any] | None = None,
    ):
        configured_fields = list(fields or [])
        if name:
            configured_fields.append(FileField(name=name, max_count=count, required=required))
        self.fields = configured_fields
        self.config = normalize_config(config)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Ensure no two fields share the same name."""
        duplicate_names = {
            field.name
            for field in self.fields
            if sum(candidate.name == field.name for candidate in self.fields) > 1
        }
        if duplicate_names:
            duplicates = ", ".join(sorted(duplicate_names))
            raise ConfigurationError(f"Duplicate file field names are not allowed: {duplicates}")

    def get_form_args(self) -> dict[str, int]:
        """Return keyword arguments for ``request.form()`` parsing limits."""
        return {
            "max_files": int(self.config.get("max_files", 1000)),
            "max_fields": int(self.config.get("max_fields", 1000)),
            "max_part_size": int(self.config.get("max_part_size", 1024 * 1024)),
        }

    async def __call__(self, request: Request) -> Store:
        """Process an upload request and return aggregated results.

        This is the main entry point when used as a FastAPI dependency.
        """
        if not self.fields:
            message = "No file fields were configured"
            return Store(status=False, error=message, message=message, errors=[message], messages=[message])

        try:
            form = await request.form(**self.get_form_args())
            results = await asyncio.gather(
                *(self.handle(file_field=field, request=request, form=form) for field in self.fields),
                return_exceptions=True,
            )
            return self.build_store(results)
        except Exception as err:
            logger.exception("Failed to process upload request in %s", self.__class__.__name__)
            message = "Unable to process uploaded files"
            error = str(err)
            return Store(status=False, error=error, message=message, errors=[error], messages=[message])

    # --- config resolution ---

    def _merge_config(self, file_field: FileField) -> dict[str, Any]:
        """Merge store-level and field-level configs, concatenating filters."""
        base_config = normalize_config(self.config)
        field_config = normalize_config(file_field.config)
        merged = {**base_config, **field_config}
        merged["filters"] = [
            *normalize_callable_list(base_config.get("filters")),
            *normalize_callable_list(field_config.get("filters")),
        ]
        return merged

    def _create_engine(self, *, config: Mapping[str, Any], request: Request, form: FormData) -> StorageEngine:
        """Instantiate the storage engine for a single field."""
        engine = config.get("storage_engine")
        if isinstance(engine, StorageEngine):
            return engine

        engine_cls = config.get("StorageEngine", getattr(self, "StorageEngine", LocalEngine))
        if not engine_cls:
            raise ConfigurationError("A storage engine must be configured")
        if not isinstance(engine_cls, type) or not issubclass(engine_cls, StorageEngine):
            raise ConfigurationError("StorageEngine must be a StorageEngine subclass")
        return engine_cls(request=request, form=form)

    # --- per-file resolution ---

    async def _resolve_filename(
        self,
        *,
        config: Mapping[str, Any],
        request: Request,
        form: FormData,
        file_field: FileField,
        file: UploadFile,
    ) -> tuple[UploadFile, str]:
        """Resolve the final filename, applying callbacks and sanitization."""
        filename = file.filename or "upload"
        filename_config = config.get("filename")

        if callable(filename_config):
            resolved = await maybe_await(filename_config(request, form, file_field.name, file))
            if isinstance(resolved, UploadFile):
                file = resolved
                filename = file.filename or filename
            elif resolved is not None:
                filename = str(resolved)
        elif filename_config is not None:
            filename = str(filename_config)

        return file, normalize_relative_filename(
            filename,
            sanitize=bool(config.get("sanitize_filename", True)),
        ).as_posix()

    async def _resolve_metadata(
        self,
        *,
        config: Mapping[str, Any],
        request: Request,
        form: FormData,
        file_field: FileField,
        file: UploadFile,
    ) -> dict[str, Any]:
        """Resolve per-file metadata from config or a callback."""
        metadata = config.get("metadata")
        if metadata is None:
            return {}
        if callable(metadata):
            resolved = await maybe_await(metadata(request, form, file_field.name, file))
            return dict(resolved or {})
        return dict(metadata)

    async def _run_filters(
        self,
        *,
        config: Mapping[str, Any],
        request: Request,
        form: FormData,
        file_field: FileField,
        file: UploadFile,
    ) -> str | None:
        """Run all filter callbacks; return the first rejection reason or ``None``."""
        for file_filter in normalize_callable_list(config.get("filters")):
            result = await maybe_await(file_filter(request, form, file_field.name, file))
            if result is True:
                continue
            if isinstance(result, str) and result:
                return result
            return f"File '{file.filename}' was rejected by a filter"
        return None

    # --- validation ---

    def _validate_known_size(self, *, file_field: FileField, file: UploadFile, config: Mapping[str, Any]) -> str | None:
        """Check size limits against the reported size, if available."""
        size = file_size_hint(file)
        if size is None:
            return None
        try:
            StorageEngine.validate_size_limits(
                size=size,
                config=config,
                field_name=file_field.name,
                filename=file.filename,
            )
        except ValidationError as err:
            return str(err)
        return None

    def _validate_type_constraints(
        self,
        *,
        file_field: FileField,
        file: UploadFile,
        config: Mapping[str, Any],
    ) -> str | None:
        """Check extension and content-type against the allow-lists."""
        raw_extensions = config.get("allowed_extensions", [])
        if isinstance(raw_extensions, str):
            raw_extensions = [raw_extensions]
        allowed_extensions = {
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in raw_extensions
        }
        if allowed_extensions:
            suffix = normalize_relative_filename(file.filename).suffix.lower()
            if suffix not in allowed_extensions:
                return (
                    f"File '{file.filename}' in field '{file_field.name}' has an unsupported extension. "
                    f"Allowed extensions: {', '.join(sorted(allowed_extensions))}"
                )

        raw_content_types = config.get("allowed_content_types", [])
        if isinstance(raw_content_types, str):
            raw_content_types = [raw_content_types]
        allowed_content_types = {content_type.lower() for content_type in raw_content_types}
        content_type = (file.content_type or "").lower()
        if allowed_content_types and content_type not in allowed_content_types:
            return (
                f"File '{file.filename}' in field '{file_field.name}' has content type '{file.content_type}'. "
                f"Allowed content types: {', '.join(sorted(allowed_content_types))}"
            )
        return None

    # --- result helpers ---

    def _failure(
        self,
        *,
        file_field: FileField,
        error: str,
        file: UploadFile | None = None,
        original_filename: str | None = None,
    ) -> FileData:
        """Build a failed :class:`FileData` from an error message."""
        filename = getattr(file, "filename", None)
        return FileData(
            field_name=file_field.name,
            filename=filename,
            original_filename=original_filename or filename,
            content_type=getattr(file, "content_type", None),
            size=file_size_hint(file),
            error=error,
            message=error,
            status=False,
        )

    # --- preparation pipeline ---

    async def _prepare_upload(
        self,
        *,
        request: Request,
        form: FormData,
        file_field: FileField,
        file: UploadFile,
    ) -> PreparedUpload | FileData:
        """Validate and prepare a single file for upload.

        Returns a :class:`PreparedUpload` on success, or a failed
        :class:`FileData` if validation rejects the file.
        """
        config = file_field.config
        original_filename = file.filename or "upload"
        file, resolved_filename = await self._resolve_filename(
            config=config,
            request=request,
            form=form,
            file_field=file_field,
            file=file,
        )
        file.filename = resolved_filename

        type_error = self._validate_type_constraints(file_field=file_field, file=file, config=config)
        if type_error:
            await file.close()
            return self._failure(
                file_field=file_field,
                file=file,
                original_filename=original_filename,
                error=type_error,
            )

        size_error = self._validate_known_size(file_field=file_field, file=file, config=config)
        if size_error:
            await file.close()
            return self._failure(
                file_field=file_field,
                file=file,
                original_filename=original_filename,
                error=size_error,
            )

        filter_error = await self._run_filters(
            config=config,
            request=request,
            form=form,
            file_field=file_field,
            file=file,
        )
        if filter_error:
            await file.close()
            return self._failure(
                file_field=file_field,
                file=file,
                original_filename=original_filename,
                error=filter_error,
            )

        metadata = await self._resolve_metadata(
            config=config,
            request=request,
            form=form,
            file_field=file_field,
            file=file,
        )
        return PreparedUpload(file=file, original_filename=original_filename, metadata=metadata)

    # --- field-level handling ---

    async def handle(self, *, file_field: FileField, request: Request, form: FormData) -> list[FileData]:
        """Process all files for a single field.

        Returns a list of :class:`FileData` containing both successes
        and failures.
        """
        merged_config = self._merge_config(file_field)
        bound_field = replace(file_field, config=merged_config)
        bound_field.config["storage_engine"] = self._create_engine(config=bound_field.config, request=request, form=form)

        files = [item for item in form.getlist(bound_field.name) if isinstance(item, UploadFile)]
        results: list[FileData] = []

        # Enforce max_count
        if len(files) > bound_field.max_count:
            overflow_files = files[bound_field.max_count:]
            files = files[:bound_field.max_count]
            for overflow_file in overflow_files:
                await overflow_file.close()
                results.append(
                    self._failure(
                        file_field=bound_field,
                        file=overflow_file,
                        error=(
                            f"Field '{bound_field.name}' accepts at most {bound_field.max_count} file(s); "
                            f"'{overflow_file.filename}' was rejected"
                        ),
                    )
                )

        # Handle missing required field
        if not files:
            if bound_field.required:
                results.append(
                    self._failure(
                        file_field=bound_field,
                        error=f"Missing required file field '{bound_field.name}'",
                    )
                )
            return results

        # Prepare all files (validate, resolve names, etc.)
        uploads: list[PreparedUpload] = []
        for file in files:
            prepared = await self._prepare_upload(
                request=request,
                form=form,
                file_field=bound_field,
                file=file,
            )
            if isinstance(prepared, FileData):
                results.append(prepared)
            else:
                uploads.append(prepared)

        if not uploads:
            return results

        # Persist all validated files concurrently
        upload_results = await asyncio.gather(
            *(self.upload(bound_field, upload) for upload in uploads),
            return_exceptions=True,
        )
        for upload, result in zip(uploads, upload_results):
            if isinstance(result, FileData):
                results.append(result)
            elif isinstance(result, Exception):
                logger.error(
                    "Unhandled upload failure for field %s",
                    bound_field.name,
                    exc_info=(type(result), result, result.__traceback__),
                )
                results.append(
                    self._failure(
                        file_field=bound_field,
                        file=upload.file,
                        original_filename=upload.original_filename,
                        error=str(result),
                    )
                )
            else:
                # Should not happen, but guard against unexpected return types
                logger.warning(
                    "Unexpected result type %s from upload for field %s",
                    type(result).__name__,
                    bound_field.name,
                )

        return results

    async def upload(self, file_field: FileField, upload: PreparedUpload) -> FileData:
        """Persist a single prepared upload via the storage engine.

        Returns a :class:`FileData` with ``status=True`` on success or
        ``status=False`` on failure.
        """
        engine = file_field.config.get("storage_engine")
        if not isinstance(engine, StorageEngine):
            raise ConfigurationError("Resolved storage engine is invalid")

        try:
            result = await engine.upload(file_field, upload.file)
            result.field_name = file_field.name
            result.original_filename = upload.original_filename
            if not result.filename:
                result.filename = upload.file.filename
            if not result.content_type:
                result.content_type = upload.file.content_type
            result.metadata = {**result.metadata, **upload.metadata}
            return result
        except FileStoreError as err:
            return self._failure(
                file_field=file_field,
                file=upload.file,
                original_filename=upload.original_filename,
                error=str(err),
            )
        except Exception as err:
            logger.exception("Unexpected upload failure in %s", self.__class__.__name__)
            return self._failure(
                file_field=file_field,
                file=upload.file,
                original_filename=upload.original_filename,
                error=str(err),
            )

    # --- store assembly ---

    @staticmethod
    def _flatten_results(value: Any) -> Iterable[FileData]:
        """Recursively yield :class:`FileData` from nested lists."""
        if isinstance(value, FileData):
            yield value
            return
        if isinstance(value, list):
            for item in value:
                yield from FileStore._flatten_results(item)

    @classmethod
    def build_store(cls, values: Iterable[Any]) -> Store:
        """Assemble a :class:`Store` from the results of :meth:`handle`.

        Handles exceptions, nested lists, and individual :class:`FileData`
        results.
        """
        store = Store()
        for value in values:
            if isinstance(value, Exception):
                error = str(value)
                store.errors.append(error)
                continue
            for file_data in cls._flatten_results(value):
                store.add(file_data)

        if store.total_files == 0:
            message = "No files were uploaded"
            store.status = False
            store.error = store.error or message
            store.message = store.message or message
            store.errors = dedupe([*store.errors, store.error])
            store.messages = dedupe([*store.messages, store.message])
            return store

        store.errors = dedupe(store.errors)
        store.messages = dedupe(store.messages)
        store.status = not store.failed_files and not store.errors

        if store.status:
            store.message = store.message or f"{store.total_files} file(s) uploaded successfully"
            store.messages = dedupe([*store.messages, store.message])
            return store

        if store.successful_files:
            store.message = store.message or "Some files failed to upload"
        else:
            store.message = store.message or "No files were uploaded successfully"
        store.error = store.error or (store.errors[0] if store.errors else store.message)
        store.messages = dedupe([*store.messages, store.message])
        store.errors = dedupe([*store.errors, store.error])
        return store
