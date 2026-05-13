# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-05-13

### Fixed

- **Critical:** `handle()` now returns both successful and failed `FileData` results. Previously, successful uploads were silently dropped.
- `FileData.to_dict()` now handles `bytes` (renders as `<N bytes>`) for JSON serialization.

### Changed

- Removed `lru_cache` from S3 client factory — clients are now created per-upload to respect credential changes.
- Removed duplicate `_detect_size` from `S3Engine` — uses inherited `detect_stream_size()`.
- Removed unused `FileField.file` attribute.
- Made Pydantic import lazy in `FileModel()` — no longer a hidden hard dependency.
- Renamed `join_s3_key` → `join_cloud_key` (alias preserved for backward compatibility).
- Renamed cloud engine factory methods to `_create_client` for consistency.

### Added

- `Store.total_size` property — sum of sizes for successful uploads.
- `__repr__` methods on `FileData`, `Store`, and `FileField`.
- `pydantic` optional extra in `pyproject.toml`.
- `S3Engine` lazy export in top-level `__init__.py`.
- Comprehensive docstrings across all public APIs.
- Full test suite (175 tests) covering data structures, utilities, engines, orchestration, and integration.
- MkDocs Material documentation site with GitHub Pages deployment.
- Ruff formatting and linting configuration.
- Coverage configuration with branch coverage reporting.
- PyPI Trusted Publishing workflow for GitHub Releases.
- PyPI package metadata, badges, and release validation checks.

## [0.2.0] — 2026-05-01

### Added

- Initial release with LocalStorage, MemoryStorage, S3Storage, GCSStorage, and AzureStorage.
- File validation for size, extension, and content type.
- Sync/async callbacks for filenames, destinations, filters, and metadata.
- Multi-field upload support with per-field configuration.
- Atomic local writes with collision handling.
- `FileModel()` helper for generating Pydantic upload models.
