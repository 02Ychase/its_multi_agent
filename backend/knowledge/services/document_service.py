import hashlib
import logging
import uuid

from repositories import chunk_repository, document_repository

logger = logging.getLogger(__name__)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def check_duplicate(file_hash: str) -> dict | None:
    return document_repository.get_by_hash(file_hash)


def create_document_record(filename: str, original_filename: str, file_hash: str, file_ext: str, storage_path: str = None) -> dict:
    document_id = generate_document_id()
    return document_repository.create_document(document_id, filename, original_filename, file_hash, file_ext, storage_path)


def update_document_status(document_id: str, status: str, error_message: str = None, chunk_count: int = None) -> None:
    document_repository.update_status(document_id, status, error_message, chunk_count)


def save_chunks(document_pk: int, document_id: str, chunks: list, title: str, original_filename: str) -> None:
    chunk_records = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{document_id}:chunk:{i}"
        chunk_records.append({
            "chunk_id": chunk_id,
            "chunk_index": i,
            "title": title,
            "content_preview": chunk.page_content[:500] if hasattr(chunk, 'page_content') else str(chunk)[:500],
            "vector_id": chunk_id,
        })
    chunk_repository.insert_chunks(document_pk, chunk_records)


def get_document(document_id: str) -> dict | None:
    return document_repository.get_by_document_id(document_id)


def list_documents(status: str = None, limit: int = 50, offset: int = 0) -> tuple:
    docs = document_repository.list_documents(status, limit, offset)
    total = document_repository.count_documents(status)
    return total, docs


def delete_document(document_id: str) -> bool:
    return document_repository.mark_deleted(document_id)


def get_chunk_vector_ids(document_pk: int) -> list:
    return chunk_repository.get_vector_ids_by_document(document_pk)


def rebuild_chunks(document_pk: int) -> None:
    chunk_repository.delete_chunks_by_document(document_pk)
