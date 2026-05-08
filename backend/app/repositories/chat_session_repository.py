from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_chat_sessions_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(128) NOT NULL,
                user_id INT NOT NULL,
                title VARCHAR(255) NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at DATETIME NULL,
                UNIQUE KEY uq_user_session (user_id, session_id),
                INDEX idx_user_updated (user_id, updated_at),
                CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("chat_sessions table initialized")
    except Exception as e:
        logger.error(f"Failed to create chat_sessions table: {e}")
        raise
    finally:
        conn.close()


def get_or_create_session(user_id: int, session_id: str) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM chat_sessions WHERE user_id = %s AND session_id = %s AND deleted_at IS NULL",
            (user_id, session_id)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO chat_sessions (user_id, session_id) VALUES (%s, %s)",
            (user_id, session_id)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_sessions_by_user(user_id: int) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_id, title, created_at, updated_at FROM chat_sessions WHERE user_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC",
            (user_id,)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def delete_session(user_id: int, session_id: str) -> bool:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_sessions SET deleted_at = NOW() WHERE user_id = %s AND session_id = %s AND deleted_at IS NULL",
            (user_id, session_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_session_owner(session_id: str) -> int | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM chat_sessions WHERE session_id = %s AND deleted_at IS NULL",
            (session_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()
