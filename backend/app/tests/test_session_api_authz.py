import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import create_fast_api
    app = create_fast_api()
    return TestClient(app)


@pytest.fixture
def mock_auth():
    with patch("api.auth_router.decode_token") as mock_decode:
        mock_decode.return_value = {"user_id": 1, "username": "test_user", "type": "access"}
        yield mock_decode


def test_missing_token_returns_401(client):
    response = client.post("/api/user_sessions", json={})
    assert response.status_code == 401


def test_user_can_list_own_sessions(client, mock_auth):
    with patch("services.conversation_service.conversation_service.get_all_sessions_memory", return_value=[
        {"session_id": "session_001", "create_time": "2026-05-09 00:00:00", "memory": [], "total_messages": 0}
    ]):
        response = client.post(
            "/api/user_sessions",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user_id"] == "test_user"


def test_request_body_user_id_cannot_override_token(client, mock_auth):
    with patch("services.conversation_service.conversation_service.get_all_sessions_memory", return_value=[]) as mock_get:
        response = client.post(
            "/api/user_sessions",
            json={"user_id": "other_user"},
            headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    mock_get.assert_called_once_with(1, "test_user")


def test_cross_user_delete_is_denied(client, mock_auth):
    with patch("services.conversation_service.conversation_service.delete_session", return_value=False):
        response = client.post(
            "/api/delete_session",
            json={"session_id": "session_belonging_to_other"},
            headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
