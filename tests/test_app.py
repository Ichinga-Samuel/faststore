from pathlib import Path

from fastapi.testclient import TestClient

from .app import app
client = TestClient(app)


def test_single_local(pdf_book):
    """Test single file upload to local storage."""
    response = client.post("/single_local", files={"book": pdf_book})
    assert response.status_code == 200
    res = response.json()
    assert res["status"] is True
    assert len(res["files"]) == 1
    file_path = Path(res["files"]["book"][0]["path"])
    assert file_path.is_file()
    assert file_path.parent == Path.cwd() / "test_results/uploads/books"


def test_multi_local(capsys, pdf_book, mobi_book, epub_book, txt_book, front_cover, back_cover, first_author,
                     second_author, third_author):
    """Test multiple file upload to local storage."""
    files = [("book_files", pdf_book), ("book_files", mobi_book), ("book_files", txt_book), ("book_files", epub_book),
             ("covers", front_cover), ("covers", back_cover), ("authors_images", first_author),
             ("authors_images", second_author)]
    response = client.post("/local_store", files=files, data={"title": "TestBook"})
    assert response.status_code == 200
    res = response.json()
    assert res["status"] is True
    assert len(res["files"]) == 3
    book_files = res["files"]["book_files"]
    authors_images = res["files"]["authors_images"]
    covers = res["files"]["covers"]
    assert len(book_files) == 2
    assert len(authors_images) == 2
    assert len(covers) == 2
    book1 = book_files[0]
    assert book1["filename"][-3:] in ["pdf", "mobi", "epub"]
    author1 = authors_images[0]
    assert Path(author1["path"]).parent == Path.cwd() / "test_results/uploads/books/TestBook"


def test_s3(capsys, pdf_book, mobi_book, epub_book, txt_book, front_cover, back_cover, first_author,
                     second_author, third_author):
    """Test multiple file upload to local storage."""
    files = [("book_files", pdf_book), ("book_files", mobi_book), ("book_files", txt_book), ("book_files", epub_book),
             ("covers", front_cover), ("covers", back_cover), ("authors_images", first_author),
             ("authors_images", second_author)]
    response = client.post("/s3_store", files=files, data={"title": "TestBook"})
    assert response.status_code == 200
    res = response.json()
    assert res["status"] is True
    assert len(res["files"]) == 3
    book_files = res["files"]["book_files"]
    authors_images = res["files"]["authors_images"]
    covers = res["files"]["covers"]
    assert len(book_files) == 2
    assert len(authors_images) == 2
    assert len(covers) == 2
    book1 = book_files[0]
    assert book1["filename"][-3:] in ["pdf", "mobi", "epub"]
