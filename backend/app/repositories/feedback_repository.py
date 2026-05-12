from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_feedback_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(128) NOT NULL,
                user_id INT NOT NULL,
                message_seq INT NULL COMMENT '关联的消息序号',
                rating TINYINT NOT NULL COMMENT '1=有用, -1=没用',
                comment TEXT NULL COMMENT '用户补充说明',
                user_query TEXT NULL COMMENT '触发此回复的用户问题',
                agent_answer TEXT NULL COMMENT 'Agent的回答（前500字符）',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session (session_id),
                INDEX idx_rating_created (rating, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("user_feedback table initialized")
    except Exception as e:
        logger.error(f"Failed to create user_feedback table: {e}")
        raise
    finally:
        conn.close()


def insert_feedback(session_id: str, user_id: int, rating: int,
                    message_seq: int = None, comment: str = None,
                    user_query: str = None, agent_answer: str = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_feedback (session_id, user_id, message_seq, rating, comment, user_query, agent_answer) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (session_id, user_id, message_seq, rating, comment,
             user_query, agent_answer[:500] if agent_answer else None)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_negative_feedback(limit: int = 50, offset: int = 0) -> list:
    """获取差评反馈，用于分析检索质量问题。"""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, user_query, agent_answer, comment, created_at "
            "FROM user_feedback WHERE rating = -1 "
            "ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cursor.fetchall()
    finally:
        conn.close()
