import asyncio
import pytest
from unittest.mock import patch, MagicMock
from schemas.tooling import ToolExecutionConfig
from services.tool_execution_service import execute_async_tool, execute_sync_tool, redact_mapping


async def fast_success_tool(query: str) -> str:
    return f"ok:{query}"


async def slow_tool():
    await asyncio.sleep(5)
    return "too slow"


async def failing_tool():
    raise RuntimeError("tool failed")


async def flaky_tool():
    if not hasattr(flaky_tool, '_called'):
        flaky_tool._called = True
        raise RuntimeError("first call fails")
    return "recovered"


def sync_success_tool(query: str) -> str:
    return f"sync-ok:{query}"


@pytest.fixture(autouse=True)
def mock_db():
    with patch("services.tool_execution_service.insert_tool_call_log") as mock_log:
        yield mock_log


@pytest.mark.asyncio
async def test_successful_async_tool():
    config = ToolExecutionConfig(timeout_seconds=5, max_attempts=1)
    result = await execute_async_tool(
        tool_name="test_tool",
        func=fast_success_tool,
        arguments={"query": "hello"},
        config=config,
    )
    assert result.status == "success"
    assert result.output == "ok:hello"
    assert result.duration_ms >= 0
    assert result.attempt_count == 1


@pytest.mark.asyncio
async def test_timeout_uses_fallback():
    config = ToolExecutionConfig(timeout_seconds=0.1, max_attempts=1, fallback_message="fallback")
    result = await execute_async_tool(
        tool_name="slow_tool",
        func=slow_tool,
        arguments={},
        config=config,
    )
    assert result.status == "fallback"
    assert result.fallback_used is True
    assert result.output == "fallback"


@pytest.mark.asyncio
async def test_exception_uses_fallback():
    config = ToolExecutionConfig(timeout_seconds=5, max_attempts=1, fallback_message="error fallback")
    result = await execute_async_tool(
        tool_name="failing_tool",
        func=failing_tool,
        arguments={},
        config=config,
    )
    assert result.status == "fallback"
    assert result.output == "error fallback"
    assert "tool failed" in result.error_message


@pytest.mark.asyncio
async def test_retry_attempts_counted():
    if hasattr(flaky_tool, '_called'):
        delattr(flaky_tool, '_called')

    config = ToolExecutionConfig(timeout_seconds=5, max_attempts=2)
    result = await execute_async_tool(
        tool_name="flaky_tool",
        func=flaky_tool,
        arguments={},
        config=config,
    )
    assert result.status == "success"
    assert result.attempt_count == 2


def test_sensitive_args_redacted():
    args = {
        "query": "hello",
        "api_key": "secret-value",
        "Authorization": "Bearer secret-token",
        "nested": {"password": "123456"},
    }
    redacted = redact_mapping(args)
    assert redacted["query"] == "hello"
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["nested"]["password"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_sync_tool_runs():
    config = ToolExecutionConfig(timeout_seconds=5, max_attempts=1)
    result = await execute_sync_tool(
        tool_name="sync_tool",
        func=sync_success_tool,
        arguments={"query": "test"},
        config=config,
    )
    assert result.status == "success"
    assert result.output == "sync-ok:test"
