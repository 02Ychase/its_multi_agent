# Agent Tool Governance Test Plan

## Related Implementation Plan

`docs/superpowers/plans/2026-05-09-agent-tool-governance.md`

## Test Objective

Verify that Agent and tool calls are controlled through timeout, retry, fallback, redaction, audit logging, process-event rendering, and routing-quality tests.

## Test Scope

In scope:

- `ToolExecutionService`
- `tool_call_logs`
- Agent-as-tool wrappers in `agent_factory.py`
- Local tool auditing for knowledge, service station, and after-sales tools
- Tool display names and error process cards
- Routing evaluation test cases
- Tool-call analytics summary endpoint

Out of scope:

- Actual LLM answer quality
- RAG document governance
- Real Baidu/DashScope MCP uptime guarantees

## Test Environment

Default automated tests should not call real LLMs or MCP servers.

Commands:

```powershell
cd backend\app
pytest tests\test_tool_execution_service.py tests\test_agent_routing.py -v
```

Integration tests:

```powershell
pytest tests -m integration -v
```

## Test Data

Mock tools:

```python
async def fast_success_tool(query: str) -> str:
    return f"ok:{query}"

async def slow_tool() -> str:
    await asyncio.sleep(2)
    return "too slow"

async def failing_tool() -> str:
    raise RuntimeError("tool failed")
```

Sensitive arguments:

```python
{
  "query": "hello",
  "api_key": "secret-value",
  "Authorization": "Bearer secret-token",
  "nested": {"password": "123456"}
}
```

## Automated Test Cases

### TOOL-DB-001: Tool Log Table Initializes Idempotently

Type: repository integration test

Steps:

1. Call `init_tool_call_logs_table()`.
2. Call it again.
3. Query `information_schema`.

Expected:

- No exception.
- `tool_call_logs` table exists.

### TOOL-EXEC-001: Successful Async Tool Returns Output And Logs Success

Type: unit test

Steps:

1. Call `execute_async_tool()` with `fast_success_tool`.
2. Query latest `tool_call_logs`.

Expected:

- Result status `success`.
- Output equals `ok:hello`.
- `duration_ms >= 0`.
- `attempt_count == 1`.
- DB log status `success`.

### TOOL-EXEC-002: Timeout Uses Fallback

Type: unit test

Setup:

Config:

```python
ToolExecutionConfig(timeout_seconds=0.1, max_attempts=1, fallback_message="fallback")
```

Steps:

1. Call `execute_async_tool()` with `slow_tool`.

Expected:

- Result status `fallback`.
- `fallback_used is True`.
- Output equals `fallback`.
- DB log status `fallback` or `timeout`, according to implementation decision. The chosen status must be consistent across tests and docs.
- Error message mentions timeout.

### TOOL-EXEC-003: Exception Uses Fallback

Type: unit test

Steps:

1. Call `execute_async_tool()` with `failing_tool` and fallback.

Expected:

- Result status `fallback`.
- Output equals configured fallback message.
- Error message contains `tool failed`.
- Log row is inserted.

### TOOL-EXEC-004: Retry Attempts Are Counted

Type: unit test

Setup:

Create a flaky tool that fails once then succeeds.

Steps:

1. Call `execute_async_tool()` with `max_attempts=2`.

Expected:

- Final status `success`.
- `attempt_count == 2`.
- Output is success output.
- Log row stores `attempt_count=2`.

### TOOL-EXEC-005: Sensitive Arguments Are Redacted

Type: unit test

Steps:

1. Call a successful tool with sensitive arguments.
2. Read `arguments_json` from DB.

Expected:

```json
{
  "query": "hello",
  "api_key": "***REDACTED***",
  "Authorization": "***REDACTED***",
  "nested": {"password": "***REDACTED***"}
}
```

Raw secrets must not appear in DB or logs.

### TOOL-EXEC-006: Sync Tool Runs In Worker Thread

Type: unit test

Steps:

1. Call `execute_sync_tool()` with a synchronous function returning `"sync-ok"`.

Expected:

- Result status `success`.
- Output equals `"sync-ok"`.
- Log row inserted.

### TOOL-AGENT-001: Technical Expert Wrapper Logs Call

Type: unit test with mocked `Runner.run`

Steps:

1. Mock `Runner.run` to return object with `final_output="technical answer"`.
2. Call `consult_technical_expert(query="电脑蓝屏")`.
3. Query tool log.

Expected:

- Function returns `technical answer`.
- Log row `tool_name="consult_technical_expert"`.
- Status `success`.

### TOOL-AGENT-002: Service Expert Wrapper Returns Fallback On Timeout

Type: unit test

Steps:

1. Mock service Agent call to sleep past timeout.
2. Call `query_service_station_and_navigate()`.

Expected:

- User-friendly fallback message returned.
- Log records timeout/fallback.

### TOOL-LOCAL-001: Knowledge Tool Logs HTTP Failure

Type: unit test with mocked httpx

Steps:

1. Mock knowledge service HTTP call to raise `httpx.ConnectError`.
2. Call `query_knowledge()`.

Expected:

- Returned value has `status="error"` or fallback payload.
- Tool log exists for `query_knowledge`.
- Error message is recorded without leaking URL credentials.

### TOOL-LOCAL-002: After-Sales Tools Are Audited

Type: unit test

Steps:

1. Call `query_order_status("ORD20240512001")`.
2. Query tool logs.

Expected:

- Tool returns order text.
- Log row exists with `tool_name="query_order_status"`.

### TOOL-SSE-001: Tool Display Name Mapping Covers All Tools

Type: unit test

Steps:

1. Check `TOOL_NAME_MAPPING` contains:
   - `consult_after_sales_expert`
   - `query_order_status`
   - `query_warranty_info`
   - `query_repair_progress`

Expected:

- All expected keys exist.
- Display values are Chinese business names.

### TOOL-SSE-002: Tool Error HTML Is Safe And Informative

Type: unit test

Steps:

1. Call `format_tool_error_html("query_knowledge", "timeout")`.

Expected:

- HTML contains display name for knowledge query.
- HTML contains `timeout`.
- HTML does not include raw stack trace.

### TOOL-ROUTE-001: Technical Intent Routes To Technical Expert

Type: routing test with mocked tools

Input:

```text
电脑开机蓝屏代码 0x0000007B 怎么办
```

Expected:

- `consult_technical_expert` selected.
- Service and after-sales tools not selected.

### TOOL-ROUTE-002: Service Intent Routes To Service Expert

Input:

```text
帮我找附近的维修站并导航过去
```

Expected:

- `query_service_station_and_navigate` selected.

### TOOL-ROUTE-003: Order Intent Routes To After-Sales Expert

Input:

```text
订单 ORD20240512001 到哪了
```

Expected:

- `consult_after_sales_expert` selected.

### TOOL-ROUTE-004: Chit-Chat Does Not Call Domain Tools

Input:

```text
你好，今天心情不太好
```

Expected:

- No domain tool called, or a direct assistant response is returned.

### TOOL-API-001: Tool Summary Endpoint Returns Aggregates

Type: API test

Steps:

1. Insert 3 tool log rows with different statuses.
2. GET `/api/tool_calls/summary` with valid token.

Expected:

```json
{
  "success": true,
  "data": {
    "total": 3,
    "by_status": [],
    "slowest": [],
    "by_tool": []
  }
}
```

## Manual Tests

### TOOL-MANUAL-001: Frontend Shows Tool Process Cards

Steps:

1. Start all services.
2. Ask `帮我找附近的维修站`.
3. Observe thinking/process area.

Expected:

- UI shows tool/process card.
- Final answer still renders.

### TOOL-MANUAL-002: External Tool Failure Degrades Gracefully

Steps:

1. Temporarily configure invalid `KNOWLEDGE_BASE_URL`.
2. Ask technical knowledge question.

Expected:

- No backend crash.
- User receives fallback response.
- Tool log records failure.

## Acceptance Gate

The feature passes when:

- Tool wrapper tests pass.
- All governed tools log calls.
- Fallbacks are user-friendly.
- Sensitive data is redacted.
- Routing tests cover all three expert categories.
- Tool summary endpoint returns meaningful aggregate data.

