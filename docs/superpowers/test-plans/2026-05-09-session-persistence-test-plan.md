# Database-Backed Session Persistence Test Plan

## Related Implementation Plan

`docs/superpowers/plans/2026-05-09-session-persistence.md`

## Test Objective

Verify that the project can safely replace JSON-based chat memory with MySQL-backed session persistence while preserving existing frontend behavior, multi-turn context, user isolation, and migration compatibility.

## Test Scope

In scope:

- MySQL table initialization for sessions, messages, events, and tool logs
- `ConversationService` behavior
- Compatibility wrapper in `SessionService`
- `/api/query`, `/api/user_sessions`, `/api/delete_session`
- Multi-turn context truncation
- JSON-to-MySQL migration script
- Frontend session list/delete request compatibility

Out of scope:

- Tool-call governance details, covered by `2026-05-09-agent-tool-governance-test-plan.md`
- Refresh-token security, covered by `2026-05-09-security-hardening-test-plan.md`
- RAG retrieval quality

## Test Environment

Local required services:

- MySQL 8.0 with database `its_db`
- Backend app with test `.env`
- Optional frontend `front/agent_web_ui` for manual checks

Recommended commands:

```powershell
cd backend\app
pytest tests\test_conversation_service.py tests\test_session_api_authz.py -v
```

Manual run:

```powershell
.\start_all.bat
```

## Test Data

Users:

| Username | Password | Purpose |
| --- | --- | --- |
| `session_user_a` | `password123` | Primary owner |
| `session_user_b` | `password123` | Authorization isolation |

Sessions:

| Session ID | Owner | Purpose |
| --- | --- | --- |
| `session_test_a_001` | `session_user_a` | Normal multi-turn |
| `session_test_b_001` | `session_user_b` | Cross-user access denial |
| `default_session` | `session_user_a` | Empty session fallback |

Messages for truncation:

```text
system: "You are a memory-aware agent assistant"
user: "turn one question"
assistant: "turn one answer"
user: "turn two question"
assistant: "turn two answer"
user: "turn three question"
assistant: "turn three answer"
user: "turn four question"
```

Expected Agent input with `max_turn=3`:

```text
system
assistant: turn one answer is excluded
user: turn two question
assistant: turn two answer
user: turn three question
assistant: turn three answer
user: turn four question
```

## Automated Test Cases

### SP-UNIT-001: Table Initialization Is Idempotent

Type: unit/integration with test database

Steps:

1. Call `init_chat_sessions_table()`.
2. Call `init_chat_messages_table()`.
3. Call `init_agent_event_tables()`.
4. Call all three again.
5. Query `information_schema.tables`.

Expected:

- No exception on repeated initialization.
- Tables exist:
  - `chat_sessions`
  - `chat_messages`
  - `agent_events`
  - `tool_call_logs`

### SP-UNIT-002: New Session Creates System And User Message

Type: service unit test

Steps:

1. Create user `session_user_a`.
2. Call `conversation_service.prepare_history(user_id, "session_user_a", "session_test_a_001", "电脑蓝屏怎么办")`.
3. Query `chat_sessions`.
4. Query `chat_messages`.

Expected:

- One session exists for `session_user_a`.
- Returned history contains:
  - one `system` message
  - one `user` message with content `电脑蓝屏怎么办`
- `chat_messages.seq` starts at 1 and increments by 1.

### SP-UNIT-003: Existing Session Appends Message

Type: service unit test

Steps:

1. Create session with one user/assistant pair.
2. Call `prepare_history()` with the same `session_id`.
3. Query message count.

Expected:

- No duplicate session row is created.
- New user message is appended to the existing session.
- `updated_at` on `chat_sessions` changes.

### SP-UNIT-004: History Truncates To Last Three Turns

Type: service unit test

Steps:

1. Insert system message plus four user/assistant turns.
2. Call `prepare_history(max_turn=3)`.

Expected:

- Returned history contains one system message plus six non-system messages.
- Oldest non-system messages outside the last three turns are excluded.
- Message order remains chronological.

### SP-UNIT-005: Assistant Final Answer Is Persisted Once

Type: service unit test

Steps:

1. Call `save_assistant_final(user_id, username, session_id, "最终回答")`.
2. Call it once more only if the implementation includes idempotency protection for the same stream ID.
3. Query `chat_messages`.

Expected:

- Normal single call appends one assistant message.
- If stream/message ID idempotency is implemented, duplicate call does not create duplicate final answer.
- If idempotency is not implemented, the test should only verify single-call persistence.

### SP-UNIT-006: Session List Shape Matches Frontend Contract

Type: service/API test

Steps:

1. Create a session with one user and one assistant message.
2. Call `get_all_sessions_memory(user_id, username)`.

Expected response item:

```json
{
  "session_id": "session_test_a_001",
  "create_time": "YYYY-MM-DD HH:MM:SS",
  "memory": [
    {"role": "user", "content": "电脑蓝屏怎么办"},
    {"role": "assistant", "content": "最终回答"}
  ],
  "total_messages": 2
}
```

System messages must not appear in `memory`.

### SP-AUTH-001: Missing Token Returns 401

Type: API test

Endpoint:

```http
POST /api/user_sessions
```

Steps:

1. Send request without `Authorization`.

Expected:

- HTTP 401.
- No session data returned.

### SP-AUTH-002: Request Body User ID Cannot Override Token

Type: API test

Steps:

1. Login as `session_user_a`.
2. Ensure `session_user_b` has a session.
3. Call `/api/user_sessions` with body:

```json
{"user_id": "session_user_b"}
```

Expected:

- HTTP 200.
- Response contains only sessions owned by `session_user_a`.
- No messages from `session_user_b` appear.

### SP-AUTH-003: Cross-User Delete Is Denied

Type: API test

Steps:

1. Login as `session_user_a`.
2. Attempt to delete `session_user_b` session:

```json
{"session_id": "session_test_b_001"}
```

Expected:

- Response success is `false`, or HTTP 404/403 depending on implementation decision.
- `session_user_b` session still exists.

### SP-API-001: Query Persists User And Assistant Messages

Type: API/integration test with Agent mocked

Mock:

- Mock `Runner.run_streamed()` to emit answer `这是模拟回答`.

Steps:

1. Login as `session_user_a`.
2. Call `/api/query` with session `session_test_a_001`.
3. Consume SSE stream until finish.
4. Query `chat_messages`.

Expected:

- One user message is persisted.
- One assistant message is persisted after stream completion.
- SSE response still contains `sagegpt/text` and `sagegpt/finish`.

### SP-MIG-001: JSON Migration Imports Existing Sessions

Type: script test

Setup:

Create temporary JSON:

```json
[
  {"role": "system", "content": "系统提示"},
  {"role": "user", "content": "历史问题"},
  {"role": "assistant", "content": "历史回答"}
]
```

Steps:

1. Create user matching folder name.
2. Run `python scripts\migrate_json_sessions_to_mysql.py`.
3. Query DB.

Expected:

- One session is created.
- Three messages are imported in order.
- Running the script again skips the same session and does not duplicate rows.

### SP-FE-001: Frontend Session List Still Loads

Type: manual UI test

Steps:

1. Start all services.
2. Login in Agent UI.
3. Send one message.
4. Refresh page.
5. Check sidebar history.

Expected:

- Sidebar shows the new session.
- Selecting session shows previous messages.
- No console error from `/api/user_sessions`.

## Regression Tests

Run after implementation:

```powershell
cd backend\app
pytest tests -m "not integration" -v
cd ..\..\front\agent_web_ui
npm run build
```

Expected:

- Backend tests pass.
- Frontend build succeeds.

## Performance Checks

### SP-PERF-001: Session List Pagination Does Not Degrade

Setup:

- Create 100 sessions for one user.

Steps:

1. Call `/api/user_sessions`.
2. Measure response time locally.

Expected:

- Response finishes within 500 ms on local MySQL for 100 sessions.
- Response size remains manageable because only visible messages are returned.

## Acceptance Gate

The feature passes testing when:

- All automated tests in this document pass.
- Manual frontend session flow works.
- No new JSON session file is created during normal chat.
- Cross-user access attempts fail.
- Migration script is safe to run twice.
