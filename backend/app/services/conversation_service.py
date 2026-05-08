from typing import List, Dict, Any
from repositories import chat_session_repository as session_repo
from repositories import chat_message_repository as message_repo
from infrastructure.logging.logger import logger


class ConversationService:
    DEFAULT_SESSION_ID = "default_session"

    def __init__(self):
        self._session_repo = session_repo
        self._message_repo = message_repo

    def prepare_history(self, user_id: int, username: str, session_id: str | None, user_input: str, max_turn: int = 3) -> List[Dict[str, Any]]:
        target_session_id = session_id if session_id else self.DEFAULT_SESSION_ID
        session_pk = self._session_repo.get_or_create_session(user_id, target_session_id)

        self._message_repo.append_message(session_pk, "user", user_input)

        messages = self._message_repo.get_messages_by_session(session_pk)
        chat_history = [{"role": row[0], "content": row[1]} for row in messages]

        return self._truncate_history(chat_history, max_turn)

    def append_message(self, user_id: int, username: str, session_id: str | None, role: str, content: str, content_kind: str | None = None, metadata: dict | None = None) -> None:
        target_session_id = session_id if session_id else self.DEFAULT_SESSION_ID
        session_pk = self._session_repo.get_or_create_session(user_id, target_session_id)
        self._message_repo.append_message(session_pk, role, content, content_kind, metadata)

    def save_assistant_final(self, user_id: int, username: str, session_id: str | None, content: str) -> None:
        self.append_message(user_id, username, session_id, "assistant", content)

    def get_all_sessions_memory(self, user_id: int, username: str) -> List[Dict[str, Any]]:
        sessions = self._session_repo.get_sessions_by_user(user_id)
        formatted = []
        for row in sessions:
            session_pk, session_id, title, created_at, updated_at = row
            messages = self._message_repo.get_messages_by_session(session_pk)
            user_visible = [
                {"role": msg[0], "content": msg[1]}
                for msg in messages
                if msg[0] != "system"
            ]
            formatted.append({
                "session_id": session_id,
                "create_time": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "",
                "memory": user_visible,
                "total_messages": len(user_visible),
            })
        return formatted

    def delete_session(self, user_id: int, session_id: str) -> bool:
        return self._session_repo.delete_session(user_id, session_id)

    def _truncate_history(self, chat_history: List[Dict[str, Any]], max_turn: int = 3) -> List[Dict[str, Any]]:
        system_msg = [msg for msg in chat_history if msg.get('role') == 'system']
        no_system_msg = [msg for msg in chat_history if msg.get('role') != 'system']
        msg_limit = max_turn * 2
        truncate_msg = no_system_msg[-msg_limit:]
        return system_msg + truncate_msg


conversation_service = ConversationService()
