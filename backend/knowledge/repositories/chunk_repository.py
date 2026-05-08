import logging
from infrastructure.database.database_pool import DatabasePool

logger = logging.getLogger(__name__)


def _get_conn():
    return DatabasePool.get_connection()


def insert_chunks(document_pk: int, chunks: list) -> None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        for chunk in chunks:
            cursor.execute(
                "INSERT INTO knowledge_document_chunks (document_pk, chunk_id, chunk_index, title, content_preview, vector_id, metadata) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (document_pk, chunk["chunk_id"], chunk["chunk_index"], chunk.get("title"), chunk.get("content_preview"), chunk.get("vector_id"), None)
            )
        conn.commit()
    finally:
        conn.close()


def delete_chunks_by_document(document_pk: int) -> None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_document_chunks WHERE document_pk = %s", (document_pk,))
        conn.commit()
    finally:
        conn.close()


def get_chunks_by_document(document_pk: int) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chunk_id, chunk_index, title, content_preview, vector_id FROM knowledge_document_chunks WHERE document_pk = %s ORDER BY chunk_index ASC",
            (document_pk,)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_vector_ids_by_document(document_pk: int) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT vector_id FROM knowledge_document_chunks WHERE document_pk = %s AND vector_id IS NOT NULL",
            (document_pk,)
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
