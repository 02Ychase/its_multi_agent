from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import create_fast_api
    app = create_fast_api()
    return TestClient(app)


@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "username": "secure_user_a",
        "email": "secure_a@example.com",
        "hashed_password": "$2b$12$test_hash",
        "is_active": True,
    }


def test_register_enforces_password_length(client):
    response = client.post("/api/auth/register", json={
        "username": "test_user",
        "email": "test@example.com",
        "password": "123"
    })
    assert response.status_code == 400


def test_login_returns_tokens(client, mock_user):
    with patch("services.auth_service.get_user_by_username", return_value=mock_user), \
         patch("services.auth_service.verify_password", return_value=True), \
         patch("services.auth_service.save_refresh_token"):
        response = client.post("/api/auth/login", json={
            "username": "secure_user_a",
            "password": "password123"
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_succeeds_before_revocation(client, mock_user):
    with patch("services.auth_service.get_user_by_username", return_value=mock_user), \
         patch("services.auth_service.verify_password", return_value=True), \
         patch("services.auth_service.is_refresh_token_active", return_value=True), \
         patch("services.auth_service.decode_token", return_value={"type": "refresh", "user_id": 1, "username": "secure_user_a", "jti": "test-jti"}):
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "valid-refresh-token"
        })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_fails_after_logout(client):
    with patch("services.auth_service.decode_token", return_value={"type": "refresh", "user_id": 1, "username": "secure_user_a", "jti": "test-jti"}), \
         patch("services.auth_service.is_refresh_token_active", return_value=False):
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "revoked-token"
        })
    assert response.status_code == 401


def test_logout_revokes_token(client):
    with patch("services.auth_service.decode_token", return_value={"type": "refresh", "user_id": 1, "username": "secure_user_a", "jti": "test-jti"}), \
         patch("services.auth_service.revoke_refresh_token", return_value=True):
        response = client.post("/api/auth/logout", json={
            "refresh_token": "valid-refresh-token"
        })
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_tampered_token_fails(client):
    with patch("services.auth_service.decode_token", return_value=None):
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "tampered-token"
        })
    assert response.status_code == 401


def test_access_token_protects_chat_apis(client):
    response = client.post("/api/user_sessions", json={})
    assert response.status_code == 401

    response = client.post("/api/delete_session", json={"session_id": "test"})
    assert response.status_code == 401
