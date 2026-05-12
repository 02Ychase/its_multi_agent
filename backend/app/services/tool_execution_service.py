import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from repositories.tool_call_repository import insert_tool_call_log
from schemas.tooling import ToolExecutionConfig, ToolExecutionResult

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "token", "authorization", "api_key", "secret", "ak"}


def redact_mapping(value: dict) -> dict:
    redacted = {}
    for key, item in value.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            redacted[key] = "***REDACTED***"
        elif isinstance(item, dict):
            redacted[key] = redact_mapping(item)
        else:
            redacted[key] = item
    return redacted


async def execute_async_tool(
    tool_name: str,
    func: Callable[..., Awaitable[Any]],
    arguments: dict,
    config: ToolExecutionConfig,
    agent_name: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> ToolExecutionResult:
    start_time = time.monotonic()
    attempt_count = 0
    last_error = None

    for attempt in range(config.max_attempts):
        attempt_count = attempt + 1
        try:
            output = await asyncio.wait_for(func(**arguments), timeout=config.timeout_seconds)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            redacted_args = redact_mapping(arguments)
            output_preview = str(output)[:config.log_output_max_chars] if output else None

            insert_tool_call_log(
                tool_name=tool_name,
                status="success",
                duration_ms=duration_ms,
                attempt_count=attempt_count,
                arguments=redacted_args,
                output_preview=output_preview,
                agent_name=agent_name,
                session_id=session_id,
                user_id=user_id,
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                status="success",
                output=output,
                duration_ms=duration_ms,
                attempt_count=attempt_count,
            )

        except asyncio.TimeoutError:
            last_error = f"Tool {tool_name} timed out after {config.timeout_seconds}s"
            logger.warning(last_error)

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"Tool {tool_name} failed: {last_error}")

    duration_ms = int((time.monotonic() - start_time) * 1000)
    redacted_args = redact_mapping(arguments)

    if config.fallback_message:
        insert_tool_call_log(
            tool_name=tool_name,
            status="fallback",
            duration_ms=duration_ms,
            attempt_count=attempt_count,
            arguments=redacted_args,
            output_preview=str(config.fallback_message)[:config.log_output_max_chars],
            error_message=last_error,
            agent_name=agent_name,
            session_id=session_id,
            user_id=user_id,
        )
        return ToolExecutionResult(
            tool_name=tool_name,
            status="fallback",
            output=config.fallback_message,
            error_message=last_error,
            duration_ms=duration_ms,
            attempt_count=attempt_count,
            fallback_used=True,
        )

    status = "timeout" if "timed out" in (last_error or "") else "error"
    insert_tool_call_log(
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        attempt_count=attempt_count,
        arguments=redacted_args,
        error_message=last_error,
        agent_name=agent_name,
        session_id=session_id,
        user_id=user_id,
    )
    return ToolExecutionResult(
        tool_name=tool_name,
        status=status,
        error_message=last_error,
        duration_ms=duration_ms,
        attempt_count=attempt_count,
    )


async def execute_sync_tool(
    tool_name: str,
    func: Callable[..., Any],
    arguments: dict,
    config: ToolExecutionConfig,
    agent_name: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> ToolExecutionResult:
    async def _wrapper(**kwargs):
        return func(**kwargs)

    return await execute_async_tool(
        tool_name=tool_name,
        func=_wrapper,
        arguments=arguments,
        config=config,
        agent_name=agent_name,
        session_id=session_id,
        user_id=user_id,
    )
