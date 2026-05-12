from unittest.mock import patch

from services.document_service import (
    check_duplicate,
    create_document_record,
    generate_document_id,
    sha256_file,
    update_document_status,
)


def test_sha256_file_returns_hex_digest(tmp_path):
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nContent")
    result = sha256_file(str(test_file))
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_generate_document_id_format():
    doc_id = generate_document_id()
    assert doc_id.startswith("doc_")
    assert len(doc_id) == 16


def test_check_duplicate_returns_existing():
    with patch("services.document_service.document_repository.get_by_hash", return_value={"document_id": "doc123", "status": "indexed"}):
        result = check_duplicate("abc123hash")
    assert result is not None
    assert result["document_id"] == "doc123"


def test_check_duplicate_returns_none_for_new():
    with patch("services.document_service.document_repository.get_by_hash", return_value=None):
        result = check_duplicate("new_hash")
    assert result is None


def test_create_document_record():
    with patch("services.document_service.document_repository.create_document", return_value={"id": 1, "document_id": "doc_abc", "status": "uploaded"}):
        result = create_document_record("test.md", "test.md", "hash123", ".md")
    assert result["status"] == "uploaded"


def test_update_document_status():
    with patch("services.document_service.document_repository.update_status") as mock_update:
        update_document_status("doc_abc", "indexed", chunk_count=5)
    mock_update.assert_called_once_with("doc_abc", "indexed", None, 5)
