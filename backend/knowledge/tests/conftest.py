import os
import sys

import pytest

# Ensure backend/knowledge is on sys.path so imports like `config.settings` work
# when running tests from the project root.
_kb_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _kb_dir not in sys.path:
    sys.path.insert(0, _kb_dir)


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test")
    monkeypatch.setenv("BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("MODEL", "test-model")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "test-embedding")
    monkeypatch.setenv("HYDE_ENABLED", "false")
    monkeypatch.setenv("RERANKER_ENABLED", "false")
