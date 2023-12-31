"""
This module sets up the test environment.
All fixtures are defined here and can be used in any test file.
"""
from pathlib import Path
import random
from string import ascii_letters, digits, whitespace

from fastapi.testclient import TestClient
from pytest import fixture

from .app import app

client = TestClient(app)

@fixture(scope='session', autouse=True)
def file():
    """
    Create a test file with random content.
    Yields:
        file: A file reader object
    """
    test_dir = Path.cwd() / 'test_data'
    test_dir.mkdir(parents=True, exist_ok=True) if not test_dir.exists() else ...

@fixture
def book_file():
    """
    Create a test file with random content.

    Yields:
        file: A file reader object
    """
    file = f'test_data/book{random.randint(1000, 9999)}.txt'
    with open(file, 'w') as fh:
        lines = [''.join(random.choices(ascii_letters + digits + whitespace, k=1000)) for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, 'rb')


@fixture
def image_file():
    """
    Create a test file with random content.
    Yields:
        file: A file reader object
    """
    file = f'test_data/image{random.randint(1000, 9999)}.png'
    with open(file, 'w') as fh:
        lines = [''.join(random.choices(ascii_letters + digits + whitespace, k=1000)) for _ in range(1000)]
        fh.writelines(lines)
    yield open(file, 'rb')