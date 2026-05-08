from typing import List, Dict, Any
from services.conversation_service import conversation_service
from models.user import get_user_by_username
from infrastructure.logging.logger import logger


class SessionService:
    """
    会话业务管理服务类 - 兼容层
    内部委托给 ConversationService，保持对外接口稳定。
    """

    DEFAULT_SESSION_ID = "default_session"

    def __init__(self):
        self._conv = conversation_service

    def _resolve_user_id(self, user_id: str) -> tuple[int, str]:
        if isinstance(user_id, int):
            return user_id, str(user_id)
        user = get_user_by_username(user_id)
        if user:
            return user["id"], user_id
        return 0, user_id

    def prepare_history(self, user_id: str, session_id: str, user_input: str, max_turn: int = 3) -> List[Dict[str, Any]]:
        numeric_id, username = self._resolve_user_id(user_id)
        return self._conv.prepare_history(numeric_id, username, session_id, user_input, max_turn)

    def save_history(self, user_id: str, session_id: str, chat_history: List[Dict[str, Any]]):
        if chat_history is None:
            return
        numeric_id, username = self._resolve_user_id(user_id)
        assistant_msgs = [m for m in chat_history if m.get("role") == "assistant"]
        if assistant_msgs:
            self._conv.save_assistant_final(numeric_id, username, session_id, assistant_msgs[-1]["content"])

    def get_all_sessions_memory(self, user_id: str) -> List[Dict[str, Any]]:
        numeric_id, username = self._resolve_user_id(user_id)
        return self._conv.get_all_sessions_memory(numeric_id, username)

    def delete_session(self, user_id: str, session_id: str) -> bool:
        numeric_id, _ = self._resolve_user_id(user_id)
        return self._conv.delete_session(numeric_id, session_id)

    def _init_system_msg_instruct(self, session_id) -> List[Dict[str, Any]]:
        return [{
            "role": "system",
            "content": f"你是一个有记忆的智能体助手，请基于上下文历史会话用户问题 (会话ID {session_id})"
        }]

    def _truncate_history(self, chat_history: List[Dict[str, Any]], max_turn: int = 3) -> List[Dict[str, Any]]:
        system_msg = [msg for msg in chat_history if msg.get('role') == 'system']
        no_system_msg = [msg for msg in chat_history if msg.get('role') != 'system']
        msg_limit = max_turn * 2
        truncate_msg = no_system_msg[-msg_limit:]
        return system_msg + truncate_msg


session_service = SessionService()
