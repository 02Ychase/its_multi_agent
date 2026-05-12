import pytest
from services.upload_validation import (
    sanitize_filename,
    validate_safe_temp_path,
    validate_upload_extension,
    validate_upload_size,
)


def test_sanitize_filename_removes_path_traversal():
    result = sanitize_filename("../../evil.md")
    assert result == "evil.md"
    assert ".." not in result
    assert "/" not in result
    assert "\\" not in result


def test_sanitize_filename_rejects_empty():
    with pytest.raises(ValueError, match="文件名不能为空"):
        sanitize_filename("")


def test_sanitize_filename_rejects_control_characters():
    result = sanitize_filename("test\x00file.md")
    assert "\x00" not in result


def test_validate_upload_extension_accepts_md():
    ext = validate_upload_extension("document.md")
    assert ext == ".md"


def test_validate_upload_extension_rejects_exe():
    with pytest.raises(ValueError, match="不支持的文件类型"):
        validate_upload_extension("malware.exe")


def test_validate_upload_size_within_limit():
    validate_upload_size(1024)


def test_validate_upload_size_exceeds_limit():
    with pytest.raises(ValueError, match="超过限制"):
        validate_upload_size(25 * 1024 * 1024)


def test_validate_safe_temp_path_within_base():
    validate_safe_temp_path("/app/uploads", "/app/uploads/test.md")


def test_validate_safe_temp_path_outside_base():
    with pytest.raises(ValueError, match="不在允许的目录范围内"):
        validate_safe_temp_path("/app/uploads", "/etc/passwd")


def test_validate_upload_extension_accepts_txt():
    ext = validate_upload_extension("readme.txt")
    assert ext == ".txt"


def test_validate_upload_extension_accepts_pdf():
    ext = validate_upload_extension("doc.pdf")
    assert ext == ".pdf"


def test_validate_upload_extension_accepts_docx():
    ext = validate_upload_extension("doc.docx")
    assert ext == ".docx"
