from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    with patch("repositories.chat_session_repository.DatabasePool") as mock_pool, \
         patch("repositories.chat_message_repository.DatabasePool") as mock_msg_pool:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_pool.get_connection.return_value = conn
        mock_msg_pool.get_connection.return_value = conn
        yield conn, cursor


@pytest.fixture
def conversation_service():
    from services.conversation_service import ConversationService
    return ConversationService()


@pytest.mark.asyncio
async def test_prepare_history_new_session(mock_db, conversation_service):
    conn, cursor = mock_db
    cursor.fetchone.return_value = None
    cursor.lastrowid = 1

    async def _mock_compress(msgs, keep_recent=3):
        """Mock compress_history that returns messages unchanged."""
        return msgs

    with patch.object(conversation_service._session_repo, "get_or_create_session", return_value=1), \
         patch.object(conversation_service._message_repo, "append_message", return_value=1), \
         patch.object(conversation_service._message_repo, "get_messages_by_session", return_value=[
             ("system", "你是一个有记忆的智能体助手", None, 1, None),
             ("user", "电脑蓝屏怎么办", None, 2, None),
         ]), \
         patch("services.conversation_service.compress_history", side_effect=_mock_compress):
        result = await conversation_service.prepare_history(1, "test_user", "session_001", "电脑蓝屏怎么办")

    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "电脑蓝屏怎么办"


@pytest.mark.asyncio
async def test_prepare_history_existing_session(mock_db, conversation_service):
    conn, cursor = mock_db

    async def _mock_compress(msgs, keep_recent=3):
        """Mock compress_history that returns messages unchanged."""
        return msgs

    with patch.object(conversation_service._session_repo, "get_or_create_session", return_value=1), \
         patch.object(conversation_service._message_repo, "append_message", return_value=1), \
         patch.object(conversation_service._message_repo, "get_messages_by_session", return_value=[
             ("system", "系统提示", None, 1, None),
             ("user", "问题1", None, 2, None),
             ("assistant", "回答1", None, 3, None),
             ("user", "问题2", None, 4, None),
             ("assistant", "回答2", None, 5, None),
             ("user", "问题3", None, 6, None),
         ]), \
         patch("services.conversation_service.compress_history", side_effect=_mock_compress):
        result = await conversation_service.prepare_history(1, "test_user", "session_001", "问题3")

    assert result[0]["role"] == "system"
    non_system = [m for m in result if m["role"] != "system"]
    assert len(non_system) == 5


def test_history_truncates_to_last_three_turns(conversation_service):
    chat_history = [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "turn one question"},
        {"role": "assistant", "content": "turn one answer"},
        {"role": "user", "content": "turn two question"},
        {"role": "assistant", "content": "turn two answer"},
        {"role": "user", "content": "turn three question"},
        {"role": "assistant", "content": "turn three answer"},
        {"role": "user", "content": "turn four question"},
    ]
    result = conversation_service._truncate_history(chat_history, max_turn=3)

    assert result[0]["role"] == "system"
    non_system = [m for m in result if m["role"] != "system"]
    assert len(non_system) == 6
    assert non_system[0]["content"] == "turn one answer"
    assert non_system[-1]["content"] == "turn four question"


def test_get_all_sessions_memory_format(conversation_service):
    with patch.object(conversation_service._session_repo, "get_sessions_by_user", return_value=[
        (1, "session_001", None, MagicMock(strftime=lambda fmt: "2026-05-09 00:25:06"), None),
    ]), \
     patch.object(conversation_service._message_repo, "get_messages_by_session", return_value=[
         ("system", "系统提示", None, 1, None),
         ("user", "电脑蓝屏怎么办", None, 2, None),
         ("assistant", "最终回答", None, 3, None),
     ]):
        result = conversation_service.get_all_sessions_memory(1, "test_user")

    assert len(result) == 1
    assert result[0]["session_id"] == "session_001"
    assert result[0]["create_time"] == "2026-05-09 00:25:06"
    assert result[0]["total_messages"] == 2
    assert result[0]["memory"][0]["role"] == "user"
    assert result[0]["memory"][1]["role"] == "assistant"


def test_delete_session_returns_true_when_owned(conversation_service):
    with patch.object(conversation_service._session_repo, "delete_session", return_value=True):
        result = conversation_service.delete_session(1, "session_001")
    assert result is True


def test_delete_session_returns_false_when_not_owned(conversation_service):
    with patch.object(conversation_service._session_repo, "delete_session", return_value=False):
        result = conversation_service.delete_session(1, "session_belonging_to_other")
    assert result is False
