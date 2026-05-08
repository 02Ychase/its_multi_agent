import hashlib
from datetime import datetime
from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_refresh_tokens_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token_hash CHAR(64) NOT NULL,
                jti VARCHAR(64) NOT NULL,
                expires_at DATETIME NOT NULL,
                revoked_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_refresh_jti (jti),
                INDEX idx_user_active (user_id, revoked_at),
                CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("refresh_tokens table initialized")
    except Exception as e:
        logger.error(f"Failed to create refresh_tokens table: {e}")
        raise
    finally:
        conn.close()


def save_refresh_token(user_id: int, token: str, jti: str, expires_at: datetime) -> None:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        token_hash = hash_token(token)
        cursor.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, jti, expires_at) VALUES (%s, %s, %s, %s)",
            (user_id, token_hash, jti, expires_at)
        )
        conn.commit()
    finally:
        conn.close()


def is_refresh_token_active(token: str, jti: str) -> bool:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        token_hash = hash_token(token)
        cursor.execute(
            "SELECT id FROM refresh_tokens WHERE token_hash = %s AND jti = %s AND revoked_at IS NULL AND expires_at > NOW()",
            (token_hash, jti)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def revoke_refresh_token(token: str, jti: str) -> bool:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        token_hash = hash_token(token)
        cursor.execute(
            "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s AND jti = %s AND revoked_at IS NULL",
            (token_hash, jti)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def revoke_all_user_refresh_tokens(user_id: int) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
