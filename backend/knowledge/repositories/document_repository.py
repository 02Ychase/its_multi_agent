import logging
from infrastructure.database.database_pool import DatabasePool

logger = logging.getLogger(__name__)


def _get_conn():
    return DatabasePool.get_connection()


def init_document_tables():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                document_id VARCHAR(64) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_hash CHAR(64) NOT NULL,
                file_ext VARCHAR(16) NOT NULL,
                status VARCHAR(32) NOT NULL,
                error_message TEXT NULL,
                chunk_count INT NOT NULL DEFAULT 0,
                uploaded_by VARCHAR(128) NULL,
                storage_path VARCHAR(512) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at DATETIME NULL,
                UNIQUE KEY uq_document_id (document_id),
                UNIQUE KEY uq_file_hash_active (file_hash, deleted_at),
                INDEX idx_status_created (status, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_document_chunks (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                document_pk BIGINT NOT NULL,
                chunk_id VARCHAR(128) NOT NULL,
                chunk_index INT NOT NULL,
                title VARCHAR(255) NULL,
                content_preview TEXT NULL,
                vector_id VARCHAR(128) NULL,
                metadata JSON NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_chunk_id (chunk_id),
                INDEX idx_document_chunk (document_pk, chunk_index),
                CONSTRAINT fk_chunks_document FOREIGN KEY (document_pk) REFERENCES knowledge_documents(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("knowledge_documents and knowledge_document_chunks tables initialized")
    except Exception as e:
        logger.error(f"Failed to create document tables: {e}")
        raise
    finally:
        conn.close()


def create_document(document_id: str, filename: str, original_filename: str, file_hash: str, file_ext: str, storage_path: str = None) -> dict:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge_documents (document_id, filename, original_filename, file_hash, file_ext, status, storage_path) VALUES (%s, %s, %s, %s, %s, 'uploaded', %s)",
            (document_id, filename, original_filename, file_hash, file_ext, storage_path)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "document_id": document_id, "status": "uploaded"}
    finally:
        conn.close()


def get_by_hash(file_hash: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, document_id, filename, status, chunk_count FROM knowledge_documents WHERE file_hash = %s AND deleted_at IS NULL AND status IN ('indexed', 'parsing', 'embedding') ORDER BY created_at DESC LIMIT 1",
            (file_hash,)
        )
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "document_id": row[1], "filename": row[2], "status": row[3], "chunk_count": row[4]}
        return None
    finally:
        conn.close()


def get_by_document_id(document_id: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, document_id, filename, original_filename, file_hash, file_ext, status, error_message, chunk_count, storage_path, created_at FROM knowledge_documents WHERE document_id = %s AND deleted_at IS NULL",
            (document_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], "document_id": row[1], "filename": row[2],
                "original_filename": row[3], "file_hash": row[4], "file_ext": row[5],
                "status": row[6], "error_message": row[7], "chunk_count": row[8],
                "storage_path": row[9], "created_at": row[10],
            }
        return None
    finally:
        conn.close()


def update_status(document_id: str, status: str, error_message: str = None, chunk_count: int = None) -> None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        if chunk_count is not None:
            cursor.execute(
                "UPDATE knowledge_documents SET status = %s, error_message = %s, chunk_count = %s WHERE document_id = %s",
                (status, error_message, chunk_count, document_id)
            )
        else:
            cursor.execute(
                "UPDATE knowledge_documents SET status = %s, error_message = %s WHERE document_id = %s",
                (status, error_message, document_id)
            )
        conn.commit()
    finally:
        conn.close()


def list_documents(status: str = None, limit: int = 50, offset: int = 0) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT id, document_id, filename, original_filename, status, chunk_count, created_at FROM knowledge_documents WHERE deleted_at IS NULL AND status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (status, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT id, document_id, filename, original_filename, status, chunk_count, created_at FROM knowledge_documents WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
        return cursor.fetchall()
    finally:
        conn.close()


def count_documents(status: str = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT COUNT(*) FROM knowledge_documents WHERE deleted_at IS NULL AND status = %s", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM knowledge_documents WHERE deleted_at IS NULL")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def mark_deleted(document_id: str) -> bool:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE knowledge_documents SET status = 'deleted', deleted_at = NOW() WHERE document_id = %s AND deleted_at IS NULL",
            (document_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
