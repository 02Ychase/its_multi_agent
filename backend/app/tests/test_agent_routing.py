from unittest.mock import patch

import pytest
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


def test_tool_summary_endpoint(client, mock_auth):
    with patch("api.routers.get_tool_call_summary", return_value={
        "total": 3,
        "by_status": [{"status": "success", "count": 2}, {"status": "fallback", "count": 1}],
        "slowest": [{"tool_name": "query_knowledge", "duration_ms": 500, "status": "success"}],
        "by_tool": [{"tool_name": "query_knowledge", "count": 3}],
    }):
        response = client.get(
            "/api/tool_calls/summary",
            headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 3


def test_tool_summary_requires_auth(client):
    response = client.get("/api/tool_calls/summary")
    assert response.status_code == 401
