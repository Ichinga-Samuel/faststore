import random
import os
import shutil
from pathlib import Path
from string import ascii_letters, digits, whitespace

import boto3
import pytest
from pytest import fixture


@pytest.fixture(scope="session")
def s3_bucket():
    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region_name = os.environ.get("AWS_DEFAULT_REGION")
    bucket_name = os.environ.get("AWS_BUCKET_NAME")
    s3 = boto3.resource('s3', region_name=region_name, aws_access_key_id=key_id, aws_secret_access_key=access_key)
    return s3.Bucket(bucket_name)


@fixture(scope="session")
def test_data(tmp_path_factory, s3_bucket):
    test_dir = tmp_path_factory.mktemp("test_data")
    yield test_dir
    shutil.rmtree(Path.cwd() / "test_results", ignore_errors=True)
    s3_bucket.object_versions.delete()


@fixture
def pdf_book(test_data):
    """
    Create a pdf test file with random content.

    Yields:
        file: A file reader object
    """
    file = test_data / "pdf_book.pdf"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def epub_book(test_data):
    """
        Create a epub test file with random content.

        Yields:
            file: A file reader object
    """
    file = test_data / "epub_book.epub"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def mobi_book(test_data):
    """
        Create a mobi test file with random content.

        Yields:
            file: A file reader object
    """
    file = test_data / "mobi_book.mobi"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1600)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def txt_book(test_data):
    """
        Create a txt test file with random content.

        Yields:
            file: A file reader object
    """
    file = test_data / "txt_book.txt"
    with open(file, "w") as fh:
        lines = ["".join(random.choices(ascii_letters + digits + whitespace, k=1000)) for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def front_cover(test_data):
    """
    Create a front cover file with random content.
    Yields:
        file: A file reader object
    """
    file = test_data / "front_cover.png"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def back_cover(test_data):
    """
    Create a back cover file with random content.
    Yields:
        file: A file reader object
    """
    file = test_data / "back_cover.jpg"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def first_author(test_data):
    """
    Create a front cover file with random content.
    Yields:
        file: A file reader object
    """
    file = test_data / "first_author.png"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")

@fixture
def second_author(test_data):
    """
    Create a front cover file with random content.
    Yields:
        file: A file reader object
    """
    file = test_data / "second_author.png"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")


@fixture
def third_author(test_data):
    """
    Create a front cover file with random content.
    Yields:
        file: A file reader object
    """
    file = test_data / "third_author.png"
    with open(file, "wb") as fh:
        lines = [("".join(random.choices(ascii_letters + digits + whitespace, k=1000))).encode() for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, "rb")
