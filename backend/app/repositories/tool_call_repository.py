import json
from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_tool_call_logs_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_call_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(128) NULL,
                user_id INT NULL,
                agent_name VARCHAR(128) NULL,
                tool_name VARCHAR(128) NOT NULL,
                arguments_json JSON NULL,
                output_preview TEXT NULL,
                status VARCHAR(32) NOT NULL,
                error_message TEXT NULL,
                duration_ms INT NOT NULL DEFAULT 0,
                attempt_count INT NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_created (session_id, created_at),
                INDEX idx_tool_status_created (tool_name, status, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("tool_call_logs table initialized")
    except Exception as e:
        logger.error(f"Failed to create tool_call_logs table: {e}")
        raise
    finally:
        conn.close()


def insert_tool_call_log(
    tool_name: str,
    status: str,
    duration_ms: int,
    attempt_count: int = 1,
    arguments: dict = None,
    output_preview: str = None,
    error_message: str = None,
    agent_name: str = None,
    session_id: str = None,
    user_id: int = None,
) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        args_json = json.dumps(arguments) if arguments else None
        cursor.execute(
            "INSERT INTO tool_call_logs (session_id, user_id, agent_name, tool_name, arguments_json, output_preview, status, error_message, duration_ms, attempt_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (session_id, user_id, agent_name, tool_name, args_json, output_preview[:1000] if output_preview else None, status, error_message, duration_ms, attempt_count)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_tool_call_summary(limit: int = 100) -> dict:
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tool_call_logs")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) as cnt FROM tool_call_logs GROUP BY status ORDER BY cnt DESC")
        by_status = [{"status": row[0], "count": row[1]} for row in cursor.fetchall()]

        cursor.execute("SELECT tool_name, duration_ms, status FROM tool_call_logs ORDER BY duration_ms DESC LIMIT 5")
        slowest = [{"tool_name": row[0], "duration_ms": row[1], "status": row[2]} for row in cursor.fetchall()]

        cursor.execute("SELECT tool_name, COUNT(*) as cnt FROM tool_call_logs GROUP BY tool_name ORDER BY cnt DESC")
        by_tool = [{"tool_name": row[0], "count": row[1]} for row in cursor.fetchall()]

        return {
            "total": total,
            "by_status": by_status,
            "slowest": slowest,
            "by_tool": by_tool,
        }
    finally:
        conn.close()
