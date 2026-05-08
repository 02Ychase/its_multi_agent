import os
import sys
import pytest

# Ensure backend/app is on sys.path so imports like `config.settings` work
# when running tests from the project root.
_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("MAIN_API_KEY", "test")
    monkeypatch.setenv("MAIN_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("SUB_API_KEY", "test")
    monkeypatch.setenv("SUB_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("MYSQL_HOST", os.getenv("MYSQL_HOST", "localhost"))
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-for-ci")
