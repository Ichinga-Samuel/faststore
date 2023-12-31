"""
Test functions for the FastStore class.
All tests are run with pytest.

Functions:
    test_local_single: Test single file upload to local storage
    test_local_multiple: Test multiple files upload to local storage
    test_s3_single: Test single file upload to S3 storage
    test_s3_multiple: Test multiple files upload to S3 storage
    test_mem_single: Test single file upload to memory storage
    test_mem_multiple: Test multiple files upload to memory storage
"""
from . import client, book_file, image_file, file


def test_s3_single(book_file):
    """
    Test single file upload to S3 storage.
    All arguments are fixtures from __init__.
    """
    response = client.post('/s3_single', files={'book': book_file})
    assert response.status_code == 200
    res = response.json()
    assert res['status'] is True
    assert res['file']['filename'] == book_file.name.rsplit('/', 1)[1]
    assert len([file for field in res['files'].values() for file in field]) == 1


def test_s3_multiple(book_file, image_file):
    """
    Test multiple files upload to S3 storage.
    All arguments are fixtures from the __init__.
    """
    files = [('author', image_file), ('book', book_file),
             ('book', book_file), ('cover', image_file)]
    response = client.post('/s3_multiple', files=files, data={'title': 'Test Book', 'author_name': 'Tester'})
    res = response.json()
    assert response.status_code == 200
    assert res['status'] is True
    assert len([file for field in res['files'].values() for file in field]) == 4


def test_local_single(book_file):
    """Test single file upload to local storage. All arguments are fixtures from the __init__."""
    response = client.post('/local_single', files={'book': book_file})
    assert response.status_code == 200
    res = response.json()
    assert res['status'] is True
    assert res['file']['filename'] == book_file.name.rsplit('/', 1)[1]
    assert len([file for field in res['files'].values() for file in field]) == 1


def test_local_multiple(book_file, image_file):
    """
    Test multiple files upload to local storage.
    All arguments are fixtures from the __init__.
    """
    files = [('author', image_file), ('books', book_file), ('books', book_file), ('cover', image_file)]
    response = client.post('/local_multiple', files=files, data={'title': 'Test Book', 'author_name': 'Tester'})
    res = response.json()
    assert response.status_code == 200
    assert res['status'] is True
    assert len([file for field in res['files'].values() for file in field]) == 4


def test_mem_single(image_file):
    """
    Test single file upload to memory storage
    All arguments are fixtures from the __init__.
    """
    response = client.post('/single_memory', files={'cover': image_file})
    assert response.status_code == 200
    res = response.json()
    assert res['status'] is True
    assert res['file']['filename'] == image_file.name.rsplit('/', 1)[1]
    assert len([file for field in res['files'].values() for file in field]) == 1


def test_mem_multiple(book_file, image_file):
    """
    Test multiple files upload to memory storage
    All arguments are fixtures from the __init__.
    """
    response = client.post('/multiple_memory', files=[('book', book_file), ('covers', image_file), ('covers', image_file)])
    res = response.json()
    assert response.status_code == 200
    assert res['status'] is True
    assert len([file for field in res['files'].values() for file in field]) == 3


def test_filestore(book_file, image_file):
    """
    Test multiple files upload to memory storage
    All arguments are fixtures from the __init__.
    """
    response = client.post('/filestore', files=[('books', book_file), ('books', book_file),
                                                ('covers', image_file), ('covers', image_file)], data={'title': 'Test Book'})
    res = response.json()
    assert response.status_code == 200
    assert len(res) == 4