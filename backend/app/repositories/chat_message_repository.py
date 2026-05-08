from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_chat_messages_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_pk BIGINT NOT NULL,
                role VARCHAR(32) NOT NULL,
                content MEDIUMTEXT NOT NULL,
                content_kind VARCHAR(32) NULL,
                seq INT NOT NULL,
                metadata JSON NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_session_seq (session_pk, seq),
                INDEX idx_session_created (session_pk, created_at),
                CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("chat_messages table initialized")
    except Exception as e:
        logger.error(f"Failed to create chat_messages table: {e}")
        raise
    finally:
        conn.close()


def append_message(session_pk: int, role: str, content: str, content_kind: str = None, metadata: dict = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(seq), 0) FROM chat_messages WHERE session_pk = %s", (session_pk,))
        max_seq = cursor.fetchone()[0]
        next_seq = max_seq + 1
        cursor.execute(
            "INSERT INTO chat_messages (session_pk, role, content, content_kind, seq, metadata) VALUES (%s, %s, %s, %s, %s, %s)",
            (session_pk, role, content, content_kind, next_seq, None)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_messages_by_session(session_pk: int, limit: int = None) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        if limit:
            cursor.execute(
                "SELECT role, content, content_kind, seq, created_at FROM chat_messages WHERE session_pk = %s ORDER BY seq ASC LIMIT %s",
                (session_pk, limit)
            )
        else:
            cursor.execute(
                "SELECT role, content, content_kind, seq, created_at FROM chat_messages WHERE session_pk = %s ORDER BY seq ASC",
                (session_pk,)
            )
        return cursor.fetchall()
    finally:
        conn.close()


def delete_messages_by_session(session_pk: int) -> bool:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_pk = %s", (session_pk,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
