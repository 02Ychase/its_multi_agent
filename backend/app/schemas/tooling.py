from typing import Any, Literal

from pydantic import BaseModel


class ToolExecutionConfig(BaseModel):
    timeout_seconds: float = 30.0
    max_attempts: int = 1
    fallback_message: str | None = None
    log_output_max_chars: int = 1000


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: Literal["success", "timeout", "error", "fallback"]
    output: Any = None
    error_message: str | None = None
    duration_ms: int
    attempt_count: int
    fallback_used: bool = False
