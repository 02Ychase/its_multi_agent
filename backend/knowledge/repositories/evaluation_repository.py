import logging
from infrastructure.database.database_pool import DatabasePool

logger = logging.getLogger(__name__)


def _get_conn():
    return DatabasePool.get_connection()


def init_evaluation_tables():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_evaluation_runs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                run_id VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL,
                metrics JSON NULL,
                case_count INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME NULL,
                UNIQUE KEY uq_eval_run_id (run_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_evaluation_cases (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                run_pk BIGINT NOT NULL,
                case_id VARCHAR(64) NOT NULL,
                question TEXT NOT NULL,
                answer MEDIUMTEXT NULL,
                contexts JSON NULL,
                metrics JSON NULL,
                latency_ms INT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_eval_cases_run FOREIGN KEY (run_pk) REFERENCES rag_evaluation_runs(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("rag_evaluation tables initialized")
    except Exception as e:
        logger.error(f"Failed to create evaluation tables: {e}")
        raise
    finally:
        conn.close()


def create_run(run_id: str, status: str, case_count: int) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rag_evaluation_runs (run_id, status, case_count) VALUES (%s, %s, %s)",
            (run_id, status, case_count)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def complete_run(run_id: str, metrics: dict) -> None:
    import json
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE rag_evaluation_runs SET status = 'completed', metrics = %s, completed_at = NOW() WHERE run_id = %s",
            (json.dumps(metrics), run_id)
        )
        conn.commit()
    finally:
        conn.close()


def insert_case(run_pk: int, case_id: str, question: str, answer: str, contexts: list, metrics: dict, latency_ms: int) -> None:
    import json
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rag_evaluation_cases (run_pk, case_id, question, answer, contexts, metrics, latency_ms) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (run_pk, case_id, question, answer, json.dumps(contexts), json.dumps(metrics), latency_ms)
        )
        conn.commit()
    finally:
        conn.close()


def list_runs(limit: int = 20) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT run_id, status, metrics, case_count, created_at, completed_at FROM rag_evaluation_runs ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        return cursor.fetchall()
    finally:
        conn.close()
