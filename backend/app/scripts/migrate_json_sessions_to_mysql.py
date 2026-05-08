"""Migrate JSON session files to MySQL.

Usage:
    cd backend/app
    python scripts/migrate_json_sessions_to_mysql.py

Iterates backend/app/user_memories/*/*.json, treats directory name as username,
resolves username to users.id, and inserts sessions/messages into MySQL.
Skips sessions that already exist (user_id, session_id).
"""

import json
import os
import sys
from pathlib import Path

# Add backend/app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.database.database_pool import DatabasePool
from models.user import get_user_by_username


def migrate():
    base_dir = Path(__file__).resolve().parent.parent / "user_memories"
    if not base_dir.exists():
        print(f"No user_memories directory found at {base_dir}")
        return

    imported_sessions = 0
    skipped_sessions = 0

    for user_dir in base_dir.iterdir():
        if not user_dir.is_dir():
            continue

        username = user_dir.name
        user = get_user_by_username(username)
        if not user:
            print(f"Skipped {username}: user not found")
            skipped_sessions += 1
            continue

        user_id = user["id"]

        for json_file in user_dir.glob("*.json"):
            session_id = json_file.stem
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            except Exception as e:
                print(f"Skipped {username}/{session_id}: read error: {e}")
                skipped_sessions += 1
                continue

            conn = DatabasePool.get_connection()
            try:
                cursor = conn.cursor()

                # Check if session already exists
                cursor.execute(
                    "SELECT id FROM chat_sessions WHERE user_id = %s AND session_id = %s",
                    (user_id, session_id)
                )
                if cursor.fetchone():
                    print(f"Skipped {username}/{session_id}: already exists")
                    skipped_sessions += 1
                    continue

                # Insert session
                cursor.execute(
                    "INSERT INTO chat_sessions (user_id, session_id) VALUES (%s, %s)",
                    (user_id, session_id)
                )
                session_pk = cursor.lastrowid

                # Insert messages
                for seq, msg in enumerate(messages, start=1):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    cursor.execute(
                        "INSERT INTO chat_messages (session_pk, role, content, seq) VALUES (%s, %s, %s, %s)",
                        (session_pk, role, content, seq)
                    )

                conn.commit()
                print(f"Imported {username}/{session_id}: {len(messages)} messages")
                imported_sessions += 1
            except Exception as e:
                conn.rollback()
                print(f"Skipped {username}/{session_id}: error: {e}")
                skipped_sessions += 1
            finally:
                conn.close()

    print(f"\nDone. imported_sessions={imported_sessions} skipped_sessions={skipped_sessions}")


if __name__ == "__main__":
    migrate()
