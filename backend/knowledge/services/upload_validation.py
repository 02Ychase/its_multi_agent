import os
import re
from pathlib import Path

from config.settings import settings


def sanitize_filename(filename: str) -> str:
    if not filename or not filename.strip():
        raise ValueError("文件名不能为空")

    name = os.path.basename(filename)
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    name = name.strip()

    if not name:
        raise ValueError("文件名无效")

    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
    stem = Path(name).stem.upper()
    if stem in reserved:
        raise ValueError(f"文件名 '{name}' 是系统保留名称")

    return name


def validate_upload_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    allowed = [e.strip() for e in settings.UPLOAD_ALLOWED_EXTENSIONS.split(",")]
    if ext not in allowed:
        raise ValueError(f"不支持的文件类型 '{ext}'，允许的类型: {', '.join(allowed)}")
    return ext


def validate_upload_size(size_bytes: int) -> None:
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        max_mb = settings.MAX_UPLOAD_BYTES / (1024 * 1024)
        raise ValueError(f"文件大小 {size_bytes / (1024 * 1024):.1f}MB 超过限制 {max_mb:.0f}MB")


def validate_safe_temp_path(base_dir: str, target_path: str) -> None:
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("目标路径不在允许的目录范围内")
