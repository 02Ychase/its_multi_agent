from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_agent_event_tables():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_pk BIGINT NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                content MEDIUMTEXT NULL,
                agent_name VARCHAR(128) NULL,
                seq INT NOT NULL,
                metadata JSON NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_seq (session_pk, seq),
                CONSTRAINT fk_agent_events_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_call_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_pk BIGINT NULL,
                tool_name VARCHAR(128) NOT NULL,
                agent_name VARCHAR(128) NULL,
                arguments_json JSON NULL,
                output_preview TEXT NULL,
                status VARCHAR(32) NOT NULL,
                error_message TEXT NULL,
                duration_ms INT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_tool_created (tool_name, created_at),
                INDEX idx_session_created (session_pk, created_at),
                CONSTRAINT fk_tool_call_logs_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("agent_events and tool_call_logs tables initialized")
    except Exception as e:
        logger.error(f"Failed to create agent event tables: {e}")
        raise
    finally:
        conn.close()


def append_agent_event(session_pk: int, event_type: str, content: str = None, agent_name: str = None, seq: int = None, metadata: dict = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        if seq is None:
            cursor.execute("SELECT COALESCE(MAX(seq), 0) FROM agent_events WHERE session_pk = %s", (session_pk,))
            seq = cursor.fetchone()[0] + 1
        cursor.execute(
            "INSERT INTO agent_events (session_pk, event_type, content, agent_name, seq, metadata) VALUES (%s, %s, %s, %s, %s, %s)",
            (session_pk, event_type, content, agent_name, seq, None)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_events_by_session(session_pk: int) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_type, content, agent_name, seq, created_at FROM agent_events WHERE session_pk = %s ORDER BY seq ASC",
            (session_pk,)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def append_tool_call_log(session_pk: int, tool_name: str, agent_name: str = None, arguments_json: str = None, output_preview: str = None, status: str = "success", error_message: str = None, duration_ms: int = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tool_call_logs (session_pk, tool_name, agent_name, arguments_json, output_preview, status, error_message, duration_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (session_pk, tool_name, agent_name, arguments_json, output_preview, status, error_message, duration_ms)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_tool_logs_by_session(session_pk: int) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tool_name, agent_name, status, duration_ms, created_at FROM tool_call_logs WHERE session_pk = %s ORDER BY created_at ASC",
            (session_pk,)
        )
        return cursor.fetchall()
    finally:
        conn.close()
