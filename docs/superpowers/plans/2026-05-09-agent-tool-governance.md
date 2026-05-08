# Agent Tool Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add timeout, retry, fallback, audit logging, and route-quality tests around Agent and tool execution so the multi-agent system behaves like a controlled enterprise workflow.

**Architecture:** Introduce a small `ToolExecutionService` that wraps high-value tool calls and records structured outcomes. Start with Agent-as-tool functions in `agent_factory.py`, then apply the same wrapper to local knowledge, service-station, and after-sales tools. Persist call logs to MySQL and stream user-friendly process events without exposing raw sensitive data.

**Tech Stack:** OpenAI Agents SDK, FastAPI, MySQL, asyncio timeout, Langfuse, pytest.

---

## File Map

Create:

- `backend/app/services/tool_execution_service.py`
- `backend/app/repositories/tool_call_repository.py`
- `backend/app/schemas/tooling.py`
- `backend/app/tests/test_tool_execution_service.py`
- `backend/app/tests/test_agent_routing.py`

Modify:

- `backend/app/multi_agent/agent_factory.py`
- `backend/app/infrastructure/tools/local/knowledge_base.py`
- `backend/app/infrastructure/tools/local/service_station.py`
- `backend/app/infrastructure/tools/local/after_sales.py`
- `backend/app/services/stream_response_service.py`
- `backend/app/utils/text_util.py`
- `backend/app/api/main.py`
- `backend/app/evaluation/test_cases.yaml`

## Governance Scope

Govern these calls first:

- `consult_technical_expert`
- `query_service_station_and_navigate`
- `consult_after_sales_expert`
- `query_knowledge`
- `resolve_user_location_from_text`
- `query_nearest_repair_shops_by_coords`
- `query_order_status`
- `query_warranty_info`
- `query_repair_progress`

Do not wrap every low-level helper function. Wrap externally meaningful tools.

## Tool Outcome Model

Use a normalized internal result:

```python
class ToolExecutionResult(BaseModel):
    tool_name: str
    status: Literal["success", "timeout", "error", "fallback"]
    output: str | dict | None = None
    error_message: str | None = None
    duration_ms: int
    attempt_count: int
    fallback_used: bool = False
```

Persist a redacted view to DB.

## Task 1: Tool Call Log Table

**Files:**

- Create: `backend/app/repositories/tool_call_repository.py`
- Modify: `backend/app/api/main.py`

- [ ] **Step 1: Add table**

```sql
CREATE TABLE IF NOT EXISTS tool_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(128) NULL,
    user_id INT NULL,
    agent_name VARCHAR(128) NULL,
    tool_name VARCHAR(128) NOT NULL,
    arguments_json JSON NULL,
    output_preview TEXT NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT NULL,
    duration_ms INT NOT NULL DEFAULT 0,
    attempt_count INT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_created (session_id, created_at),
    INDEX idx_tool_status_created (tool_name, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- [ ] **Step 2: Repository functions**

Repository methods:

| Method | Required behavior |
| --- | --- |
| `init_tool_call_logs_table() -> None` | Create the tool-call audit table when missing. |
| `insert_tool_call_log(...) -> int` | Insert a redacted tool-call record and return its primary key. Required arguments are `tool_name`, `status`, `duration_ms`, and `attempt_count`; optional arguments are `arguments`, `output_preview`, `error_message`, `agent_name`, `session_id`, and `user_id`. |

- [ ] **Step 3: Initialize on startup**

Call `init_tool_call_logs_table()` in `backend/app/api/main.py` lifespan after user table initialization.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/repositories/tool_call_repository.py backend/app/api/main.py
git commit -m "feat: add tool call audit log table"
```

## Task 2: Tool Execution Service

**Files:**

- Create: `backend/app/services/tool_execution_service.py`
- Create: `backend/app/schemas/tooling.py`
- Test: `backend/app/tests/test_tool_execution_service.py`

- [ ] **Step 1: Add schemas**

```python
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
```

- [ ] **Step 2: Add redaction**

Redact keys containing:

```python
SENSITIVE_KEYS = {"password", "token", "authorization", "api_key", "secret", "ak"}
```

Function:

```python
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
```

- [ ] **Step 3: Implement async wrapper**

Implement `execute_async_tool` with this exact public signature:

```python
async def execute_async_tool(
    tool_name: str,
    func: Callable[..., Awaitable[Any]],
    arguments: dict,
    config: ToolExecutionConfig,
    agent_name: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> ToolExecutionResult:
    """Run one async tool with timeout, retry, fallback, redaction, and audit logging."""
```

Rules:

- Use `asyncio.wait_for()` for timeout.
- Retry up to `max_attempts`.
- On timeout, set status `timeout`.
- On exception, set status `error`.
- If fallback message exists, output fallback message and set `fallback_used=True`, status `fallback`.
- Always log to `tool_call_logs`.

- [ ] **Step 4: Implement sync wrapper**

Implement `execute_sync_tool` with this public signature and delegate to `execute_async_tool` through `asyncio.to_thread`:

```python
async def execute_sync_tool(
    tool_name: str,
    func: Callable[..., Any],
    arguments: dict,
    config: ToolExecutionConfig,
    agent_name: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> ToolExecutionResult:
    """Run one sync tool in a worker thread with the same governance behavior."""
```

- [ ] **Step 5: Tests**

Test:

- Successful async function logs success.
- Timeout returns fallback when configured.
- Exception returns fallback when configured.
- Sensitive args are redacted before persistence.

Run:

```powershell
cd backend\app
pytest tests\test_tool_execution_service.py -v
```

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/tool_execution_service.py backend/app/schemas/tooling.py backend/app/tests/test_tool_execution_service.py
git commit -m "feat: add governed tool execution wrapper"
```

## Task 3: Wrap Agent-As-Tool Functions

**Files:**

- Modify: `backend/app/multi_agent/agent_factory.py`

- [ ] **Step 1: Define configs**

Use conservative defaults:

```python
TECHNICAL_AGENT_TOOL_CONFIG = ToolExecutionConfig(
    timeout_seconds=90,
    max_attempts=1,
    fallback_message="技术专家暂时不可用，请稍后再试，或先描述设备型号和故障现象。"
)

SERVICE_AGENT_TOOL_CONFIG = ToolExecutionConfig(
    timeout_seconds=90,
    max_attempts=1,
    fallback_message="服务站与导航查询暂时不可用，请稍后再试，或提供更明确的城市/地址。"
)

AFTER_SALES_TOOL_CONFIG = ToolExecutionConfig(
    timeout_seconds=30,
    max_attempts=1,
    fallback_message="售后查询暂时不可用，请稍后再试，并确认订单号或工单号是否正确。"
)
```

- [ ] **Step 2: Wrap `Runner.run` calls**

For `consult_technical_expert`, move the current logic into an inner async function:

```python
async def _run():
    result = await Runner.run(
        technical_agent,
        input=query,
        run_config=RunConfig(tracing_disabled=True)
    )
    return result.final_output

result = await execute_async_tool(
    tool_name="consult_technical_expert",
    func=lambda query: _run(),
    arguments={"query": query},
    config=TECHNICAL_AGENT_TOOL_CONFIG,
    agent_name="orchestrator",
)
return result.output
```

Apply same pattern to service and after-sales tools.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/multi_agent/agent_factory.py
git commit -m "feat: govern orchestrator agent tool calls"
```

## Task 4: Wrap Local Tools

**Files:**

- Modify: `backend/app/infrastructure/tools/local/knowledge_base.py`
- Modify: `backend/app/infrastructure/tools/local/service_station.py`
- Modify: `backend/app/infrastructure/tools/local/after_sales.py`

- [ ] **Step 1: Knowledge tool timeout and fallback**

`query_knowledge` already uses httpx timeout. Add governed execution around the internal HTTP call:

```python
KNOWLEDGE_TOOL_CONFIG = ToolExecutionConfig(
    timeout_seconds=65,
    max_attempts=1,
    fallback_message={"status": "error", "error_msg": "知识库暂时不可用，请稍后再试。"}
)
```

Return `result.output`.

- [ ] **Step 2: Service station DB tool**

Wrap `query_nearest_repair_shops_by_coords` with sync execution. Fallback should be JSON string:

```json
{"ok": false, "error": "服务站数据库暂时不可用，请稍后再试"}
```

- [ ] **Step 3: After-sales mock tools**

Wrap after-sales functions with `timeout_seconds=10`, `max_attempts=1`. Even though mock data is local, logging these calls improves auditability.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/infrastructure/tools/local/knowledge_base.py backend/app/infrastructure/tools/local/service_station.py backend/app/infrastructure/tools/local/after_sales.py
git commit -m "feat: audit local tool execution"
```

## Task 5: Stream Process Events For Governed Tools

**Files:**

- Modify: `backend/app/services/stream_response_service.py`
- Modify: `backend/app/utils/text_util.py`

- [ ] **Step 1: Normalize tool display names**

Add missing mapping:

```python
"consult_after_sales_expert": "订单售后专家",
"query_order_status": "订单状态查询",
"query_warranty_info": "保修信息查询",
"query_repair_progress": "维修进度查询",
```

- [ ] **Step 2: Add failure process card**

Add a helper:

```python
def format_tool_error_html(tool_name: str, message: str) -> str:
    display_name = TOOL_NAME_MAPPING.get(tool_name, tool_name)
    return f"""
<div class="tech-process-card tool-error">
  <div class="tech-process-header">
    <span class="tech-icon">!</span>
    <span class="tech-label">工具调用异常</span>
  </div>
  <div class="tech-process-body">
    <span class="tech-text">{display_name}: {message}</span>
  </div>
</div>
"""
```

- [ ] **Step 3: Keep existing SSE envelope**

Do not change frontend parser. Continue sending `ContentKind.PROCESS` text packets.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/stream_response_service.py backend/app/utils/text_util.py
git commit -m "feat: improve tool process event rendering"
```

## Task 6: Agent Routing Evaluation

**Files:**

- Modify: `backend/app/evaluation/test_cases.yaml`
- Create: `backend/app/tests/test_agent_routing.py`

- [ ] **Step 1: Define routing cases**

Add cases for:

- Technical question routes to `consult_technical_expert`.
- Service station request routes to `query_service_station_and_navigate`.
- Order query routes to `consult_after_sales_expert`.
- Mixed request invokes two tools.
- Chit-chat should not call domain tools.

- [ ] **Step 2: Test prompt/tool selection without external calls**

Mock `Runner.run` or tool functions to avoid real LLM calls where possible. If testing the real model, mark tests:

```python
@pytest.mark.integration
```

Default CI should skip integration tests.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/evaluation/test_cases.yaml backend/app/tests/test_agent_routing.py
git commit -m "test: add agent routing quality cases"
```

## Task 7: Tool Call Analytics Endpoint

**Files:**

- Modify: `backend/app/api/routers.py`
- Modify: `backend/app/repositories/tool_call_repository.py`

- [ ] **Step 1: Add summary query**

Repository method:

Repository method:

```python
def get_tool_call_summary(limit: int = 100) -> dict:
    """Return total call count plus grouped summaries by status, slowest calls, and calls by tool."""
```

Return shape:

```json
{
  "total": 42,
  "by_status": [{"status": "success", "count": 38}, {"status": "fallback", "count": 4}],
  "slowest": [{"tool_name": "query_knowledge", "duration_ms": 6123, "status": "success"}],
  "by_tool": [{"tool_name": "query_knowledge", "count": 20}, {"tool_name": "consult_technical_expert", "count": 12}]
}
```

- [ ] **Step 2: Add protected endpoint**

```python
@router.get("/api/tool_calls/summary")
def tool_call_summary(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": get_tool_call_summary()}
```

If no admin role exists, allow only local development or omit this endpoint from UI. The endpoint is mainly for demos and interview screenshots.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/routers.py backend/app/repositories/tool_call_repository.py
git commit -m "feat: add tool call analytics summary endpoint"
```

## Acceptance Criteria

- Every high-value tool call is logged with status, duration, and redacted arguments.
- Tool timeout produces controlled fallback instead of uncaught failure.
- Agent-as-tool calls use the governance wrapper.
- Local knowledge/service/after-sales tools are audited.
- Frontend SSE behavior remains compatible.
- Routing evaluation cases are documented and testable.
- Tool summary endpoint returns aggregate data.

## Resume Bullet

> Implemented tool-call governance for a multi-agent system, including timeout control, fallback responses, structured audit logs, redaction, route-quality tests, and operational tool analytics.
