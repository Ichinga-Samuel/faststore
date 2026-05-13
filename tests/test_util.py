"""Tests for filestore.util — utility functions."""

from __future__ import annotations

from pathlib import Path

from filestore.util import (
    as_absolute_directory,
    build_public_url,
    dedupe,
    ensure_unique_path,
    file_size_hint,
    join_cloud_key,
    join_s3_key,
    maybe_await,
    normalize_callable_list,
    normalize_config,
    normalize_relative_filename,
    sanitize_path_part,
)

# ── maybe_await ───────────────────────────────────────────────────────


class TestMaybeAwait:
    async def test_sync_value(self):
        result = await maybe_await(42)
        assert result == 42

    async def test_awaitable_value(self):
        async def coro():
            return "hello"

        result = await maybe_await(coro())
        assert result == "hello"

    async def test_none_value(self):
        result = await maybe_await(None)
        assert result is None


# ── normalize_config ──────────────────────────────────────────────────


class TestNormalizeConfig:
    def test_none(self):
        assert normalize_config(None) == {}

    def test_empty_dict(self):
        assert normalize_config({}) == {}

    def test_copies_dict(self):
        original = {"a": 1}
        result = normalize_config(original)
        result["b"] = 2
        assert "b" not in original

    def test_from_mapping(self):
        from collections import OrderedDict

        result = normalize_config(OrderedDict(x=1, y=2))
        assert result == {"x": 1, "y": 2}


# ── normalize_callable_list ──────────────────────────────────────────


class TestNormalizeCallableList:
    def test_none(self):
        assert normalize_callable_list(None) == []

    def test_single_callable(self):
        fn = lambda: None
        assert normalize_callable_list(fn) == [fn]

    def test_list_with_nones(self):
        fn = lambda: None
        assert normalize_callable_list([fn, None, fn]) == [fn, fn]

    def test_tuple(self):
        fn = lambda: None
        assert normalize_callable_list((fn, None)) == [fn]

    def test_empty_list(self):
        assert normalize_callable_list([]) == []


# ── dedupe ────────────────────────────────────────────────────────────


class TestDedupe:
    def test_empty(self):
        assert dedupe([]) == []

    def test_removes_duplicates(self):
        assert dedupe(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_removes_empty_strings(self):
        assert dedupe(["", "a", "", "b"]) == ["a", "b"]

    def test_preserves_order(self):
        assert dedupe(["c", "b", "a"]) == ["c", "b", "a"]

    def test_all_empty(self):
        assert dedupe(["", "", ""]) == []


# ── sanitize_path_part ───────────────────────────────────────────────


class TestSanitizePathPart:
    def test_normal(self):
        assert sanitize_path_part("hello.txt") == "hello.txt"

    def test_traversal_dot(self):
        assert sanitize_path_part(".") == ""

    def test_traversal_dotdot(self):
        assert sanitize_path_part("..") == ""

    def test_empty(self):
        assert sanitize_path_part("") == ""

    def test_drive_letter(self):
        assert sanitize_path_part("C:") == ""

    def test_sanitize_special_chars(self):
        assert sanitize_path_part("hello world!.txt", sanitize=True) == "hello_world_.txt"

    def test_no_sanitize(self):
        assert sanitize_path_part("hello world.txt", sanitize=False) == "hello world.txt"

    def test_whitespace_only(self):
        assert sanitize_path_part("   ") == ""


# ── normalize_relative_filename ──────────────────────────────────────


class TestNormalizeRelativeFilename:
    def test_simple_filename(self):
        result = normalize_relative_filename("report.pdf")
        assert result == Path("report.pdf")

    def test_backslash_normalization(self):
        result = normalize_relative_filename("uploads\\report.pdf")
        assert result == Path("uploads", "report.pdf")

    def test_removes_traversal(self):
        result = normalize_relative_filename("../../etc/passwd")
        assert ".." not in str(result)
        assert result == Path("etc", "passwd")

    def test_none_uses_default(self):
        result = normalize_relative_filename(None)
        assert result == Path("upload")

    def test_empty_string_uses_default(self):
        result = normalize_relative_filename("")
        assert result == Path("upload")

    def test_custom_default(self):
        result = normalize_relative_filename(None, default_name="file.bin")
        assert result == Path("file.bin")

    def test_sanitize_off(self):
        result = normalize_relative_filename("my file (1).txt", sanitize=False)
        assert result == Path("my file (1).txt")

    def test_drive_letter_stripped(self):
        result = normalize_relative_filename("C:/uploads/test.txt")
        assert result == Path("uploads", "test.txt")


# ── ensure_unique_path ───────────────────────────────────────────────


class TestEnsureUniquePath:
    def test_nonexistent_returns_same(self, tmp_path: Path):
        path = tmp_path / "new.txt"
        assert ensure_unique_path(path) == path

    def test_existing_gets_suffix(self, tmp_path: Path):
        path = tmp_path / "existing.txt"
        path.write_text("data")
        unique = ensure_unique_path(path)
        assert unique != path
        assert unique.name == "existing-1.txt"

    def test_multiple_existing(self, tmp_path: Path):
        for name in ["f.txt", "f-1.txt", "f-2.txt"]:
            (tmp_path / name).write_text("data")
        unique = ensure_unique_path(tmp_path / "f.txt")
        assert unique.name == "f-3.txt"


# ── as_absolute_directory ────────────────────────────────────────────


class TestAsAbsoluteDirectory:
    def test_none_returns_cwd(self):
        result = as_absolute_directory(None)
        assert result == Path.cwd()

    def test_absolute_returned_as_is(self, tmp_path: Path):
        result = as_absolute_directory(tmp_path)
        assert result == tmp_path

    def test_relative_resolved_against_cwd(self):
        result = as_absolute_directory("uploads")
        assert result.is_absolute()
        assert result == Path.cwd() / "uploads"


# ── build_public_url ─────────────────────────────────────────────────


class TestBuildPublicUrl:
    def test_none_base_url(self):
        assert build_public_url(None, Path("file.txt")) is None

    def test_none_path(self):
        assert build_public_url("/media", None) is None

    def test_simple(self):
        url = build_public_url("/media", Path("uploads/file.txt"))
        assert url == "/media/uploads/file.txt"

    def test_trailing_slash(self):
        url = build_public_url("/media/", Path("file.txt"))
        assert url == "/media/file.txt"

    def test_special_characters_encoded(self):
        url = build_public_url("/media", Path("my file.txt"))
        assert "my%20file.txt" in url


# ── join_cloud_key ───────────────────────────────────────────────────


class TestJoinCloudKey:
    def test_simple(self):
        assert join_cloud_key("prefix", "file.txt") == "prefix/file.txt"

    def test_none_prefix(self):
        assert join_cloud_key(None, "file.txt") == "file.txt"

    def test_empty_prefix(self):
        assert join_cloud_key("", "file.txt") == "file.txt"

    def test_backslash_normalization(self):
        assert join_cloud_key("a\\b", "c\\d.txt") == "a/b/c/d.txt"

    def test_alias(self):
        assert join_s3_key is join_cloud_key


# ── file_size_hint ───────────────────────────────────────────────────


class TestFileSizeHint:
    def test_none_file(self):
        assert file_size_hint(None) is None

    def test_no_size_attribute(self):
        from unittest.mock import MagicMock

        file = MagicMock(spec=[])
        assert file_size_hint(file) is None

    def test_negative_size(self):
        from unittest.mock import MagicMock

        file = MagicMock()
        file.size = -1
        assert file_size_hint(file) is None

    def test_valid_size(self):
        from unittest.mock import MagicMock

        file = MagicMock()
        file.size = 1024
        assert file_size_hint(file) == 1024

    def test_zero_size(self):
        from unittest.mock import MagicMock

        file = MagicMock()
        file.size = 0
        assert file_size_hint(file) == 0
