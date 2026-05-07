from infrastructure.database.database_pool import db_pool
from infrastructure.logging.logger import logger


def init_users_table():
    """Create users table if it doesn't exist."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("Users table initialized")
    except Exception as e:
        logger.error(f"Failed to create users table: {e}")
        raise
    finally:
        if conn:
            db_pool.release_connection(conn)


def get_user_by_username(username: str) -> dict | None:
    """Get user by username."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, hashed_password, is_active FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "hashed_password": row[3],
                "is_active": bool(row[4]),
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get user by username: {e}")
        return None
    finally:
        if conn:
            db_pool.release_connection(conn)


def create_user(username: str, email: str, hashed_password: str) -> dict | None:
    """Create a new user and return user info."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        logger.info(f"User created: {username} (id={user_id})")
        return {"id": user_id, "username": username, "email": email}
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return None
    finally:
        if conn:
            db_pool.release_connection(conn)
