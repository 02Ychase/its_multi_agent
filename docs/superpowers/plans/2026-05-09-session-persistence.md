# Database-Backed Session Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace file-based JSON conversation memory with MySQL-backed sessions, messages, Agent events, and tool-call logs while keeping the current frontend API behavior stable.

**Architecture:** Keep `SessionService` as the business boundary. Introduce database repositories for sessions/messages/events, add migrations and JSON import tooling, then switch `MultiAgentService` to persist final assistant messages and process/tool events to MySQL. The old JSON repository remains only as a migration source and optional local fallback during the transition.

**Tech Stack:** FastAPI, PyMySQL/DBUtils, MySQL 8, Pydantic, pytest, existing `DatabasePool`.

---

## File Map

Create:

- `backend/app/repositories/chat_session_repository.py`  
  Owns CRUD for `chat_sessions`.
- `backend/app/repositories/chat_message_repository.py`  
  Owns append/load/delete for `chat_messages`.
- `backend/app/repositories/agent_event_repository.py`  
  Owns append/load for `agent_events` and `tool_call_logs`.
- `backend/app/services/conversation_service.py`  
  New high-level service that replaces file-oriented behavior while preserving `SessionService` method semantics.
- `backend/app/scripts/migrate_json_sessions_to_mysql.py`  
  Imports `backend/app/user_memories/**/*.json` into MySQL.
- `backend/app/tests/test_conversation_service.py`
- `backend/app/tests/test_session_api_authz.py`

Modify:

- `backend/app/api/main.py`  
  Initialize new tables on startup.
- `backend/app/api/routers.py`  
  Use authenticated username/user ID instead of trusting request body user ID.
- `backend/app/services/session_service.py`  
  Convert into a compatibility wrapper over `ConversationService`.
- `backend/app/services/agent_service.py`  
  Persist final answer and optionally stream events.
- `backend/app/schemas/request.py`  
  Make session APIs no longer require caller-supplied `user_id` after frontend migration.
- `front/agent_web_ui/src/stores/chat.js`  
  Stop sending `user_id` for session list/delete after backend supports token identity.

## Database Schema

Use the existing `users.id` integer as the authoritative owner key. Keep `username` only for display.

```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    user_id INT NOT NULL,
    title VARCHAR(255) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uq_user_session (user_id, session_id),
    INDEX idx_user_updated (user_id, updated_at),
    CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_pk BIGINT NOT NULL,
    role VARCHAR(32) NOT NULL,
    content MEDIUMTEXT NOT NULL,
    content_kind VARCHAR(32) NULL,
    seq INT NOT NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_session_seq (session_pk, seq),
    INDEX idx_session_created (session_pk, created_at),
    CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_pk BIGINT NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    content MEDIUMTEXT NULL,
    agent_name VARCHAR(128) NULL,
    seq INT NOT NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_seq (session_pk, seq),
    CONSTRAINT fk_agent_events_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tool_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_pk BIGINT NULL,
    tool_name VARCHAR(128) NOT NULL,
    agent_name VARCHAR(128) NULL,
    arguments_json JSON NULL,
    output_preview TEXT NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT NULL,
    duration_ms INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tool_created (tool_name, created_at),
    INDEX idx_session_created (session_pk, created_at),
    CONSTRAINT fk_tool_call_logs_session FOREIGN KEY (session_pk) REFERENCES chat_sessions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## API Compatibility

Keep these endpoints initially:

- `POST /api/query`
- `POST /api/user_sessions`
- `POST /api/delete_session`

Behavior changes:

- `current_user` from JWT becomes the owner.
- `request.user_id` is ignored during a compatibility period.
- Future frontend change removes `user_id` from payload.

Returned `sessions` should still look like the current frontend expects:

```json
{
  "success": true,
  "user_id": "chenmo",
  "total_sessions": 1,
  "sessions": [
    {
      "session_id": "session_1778257906851_8m2lzk9v1",
      "create_time": "2026-05-09 00:25:06",
      "memory": [
        {"role": "user", "content": "电脑蓝屏怎么办"},
        {"role": "assistant", "content": "可以先记录蓝屏代码并重启进入安全模式"}
      ],
      "total_messages": 2
    }
  ]
}
```

## Task 1: Table Initialization

**Files:**

- Create: `backend/app/repositories/chat_session_repository.py`
- Create: `backend/app/repositories/chat_message_repository.py`
- Create: `backend/app/repositories/agent_event_repository.py`
- Modify: `backend/app/api/main.py`

- [ ] **Step 1: Add repository table initialization methods**

Each repository module should expose an `init_*_table()` function. Use `DatabasePool.get_connection()` and close connections in `finally`.

The main startup flow should call:

```python
from repositories.chat_session_repository import init_chat_sessions_table
from repositories.chat_message_repository import init_chat_messages_table
from repositories.agent_event_repository import init_agent_event_tables

init_chat_sessions_table()
init_chat_messages_table()
init_agent_event_tables()
```

- [ ] **Step 2: Run backend import check**

Run:

```powershell
cd backend\app
python -c "from api.main import create_fast_api; app=create_fast_api(); print(app.title)"
```

Expected:

```text
ITS API
```

- [ ] **Step 3: Commit**

```powershell
git add backend/app/repositories/chat_session_repository.py backend/app/repositories/chat_message_repository.py backend/app/repositories/agent_event_repository.py backend/app/api/main.py
git commit -m "feat: add MySQL tables for chat sessions and agent events"
```

## Task 2: Conversation Service

**Files:**

- Create: `backend/app/services/conversation_service.py`
- Modify: `backend/app/services/session_service.py`
- Test: `backend/app/tests/test_conversation_service.py`

- [ ] **Step 1: Define service methods**

`ConversationService` must provide:

`ConversationService` must expose these concrete methods:

| Method | Required behavior |
| --- | --- |
| `prepare_history(user_id: int, username: str, session_id: str | None, user_input: str, max_turn: int = 3) -> list[dict]` | Ensure session exists, append the current user message, return system prompt plus recent messages for Agent input. |
| `append_message(user_id: int, username: str, session_id: str | None, role: str, content: str, content_kind: str | None = None, metadata: dict | None = None) -> None` | Append one message using the next sequence number for the owned session. |
| `save_assistant_final(user_id: int, username: str, session_id: str | None, content: str) -> None` | Append the final assistant answer for the owned session. |
| `get_all_sessions_memory(user_id: int, username: str) -> list[dict]` | Return the existing frontend-compatible session list shape, filtered by owner. |
| `delete_session(user_id: int, session_id: str) -> bool` | Delete or soft-delete only the session owned by `user_id`; return `False` for missing or unauthorized sessions. |

Rules:

- Create the session lazily when the first message is appended.
- `prepare_history()` appends the current user input in DB before returning Agent input.
- Preserve system prompt behavior.
- Return only the last `max_turn * 2` non-system messages plus the system message.
- Do not expose messages from another `user_id`.

- [ ] **Step 2: Make `SessionService` a compatibility wrapper**

Keep imports stable by replacing `SessionService` internals with calls to `ConversationService`. If a caller still passes username instead of numeric ID, resolve the user through `models.user.get_user_by_username()`.

- [ ] **Step 3: Add tests**

Test cases:

- New session returns system + current user message.
- Existing session returns last 3 turns only.
- User A cannot load User B session.
- Delete marks or removes only the owner session.

Run:

```powershell
cd backend\app
pytest tests\test_conversation_service.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/conversation_service.py backend/app/services/session_service.py backend/app/tests/test_conversation_service.py
git commit -m "feat: move session memory from JSON files to MySQL"
```

## Task 3: API Authorization And Payload Migration

**Files:**

- Modify: `backend/app/api/routers.py`
- Modify: `backend/app/schemas/request.py`
- Test: `backend/app/tests/test_session_api_authz.py`

- [ ] **Step 1: Use token identity**

In each authenticated route, derive ownership from:

```python
current_user["user_id"]
current_user["username"]
```

Do not trust `request.user_id` for selecting data.

- [ ] **Step 2: Keep request models backward compatible**

Change `UserSessionsRequest.user_id` to optional:

```python
class UserSessionsRequest(BaseModel):
    user_id: str | None = None
```

Keep `DeleteSessionRequest.session_id` required.

- [ ] **Step 3: Add API tests**

Tests should verify:

- No token returns 401.
- User can list own sessions.
- User cannot delete a session created by another user.
- Legacy payload with `user_id` does not override token owner.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/routers.py backend/app/schemas/request.py backend/app/tests/test_session_api_authz.py
git commit -m "fix: enforce token-owned access for chat session APIs"
```

## Task 4: Agent Final Answer Persistence

**Files:**

- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/app/services/stream_response_service.py`

- [ ] **Step 1: Persist final assistant answer once**

Current `MultiAgentService.process_task()` appends to `chat_history` and saves the full history. Replace that with:

```python
conversation_service.save_assistant_final(
    user_id=current_user_id,
    username=username,
    session_id=session_id,
    content=format_agent_result,
)
```

If `ChatMessageRequest` does not carry numeric user ID, enrich the request in the API route or change `process_task()` to accept `current_user`.

- [ ] **Step 2: Persist process events optionally**

`process_stream_response()` can return both SSE strings and structured event data, or `MultiAgentService` can parse generated chunks before yielding. Keep the first implementation simple:

- Persist only final user/assistant messages.
- Leave `agent_events` and `tool_call_logs` for the Agent Tool Governance workstream.

- [ ] **Step 3: Manual verification**

Start backend and send two messages in one session. Confirm `chat_messages` contains:

```text
system
user
assistant
user
assistant
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/agent_service.py backend/app/services/stream_response_service.py
git commit -m "feat: persist agent chat messages through conversation service"
```

## Task 5: JSON Session Migration

**Files:**

- Create: `backend/app/scripts/migrate_json_sessions_to_mysql.py`

- [ ] **Step 1: Implement migration script**

Script behavior:

- Iterate `backend/app/user_memories/*/*.json`.
- Treat directory name as username.
- Resolve username to `users.id`; skip missing users and print them.
- Insert session and messages with increasing `seq`.
- Avoid duplicate import if `(user_id, session_id)` already exists.

Command:

```powershell
cd backend\app
python scripts\migrate_json_sessions_to_mysql.py
```

Expected output example:

```text
Imported ycz/default_session: 7 messages
Skipped chenmo/session_1778257906851_8m2lzk9v1: user not found
Done. imported_sessions=4 skipped_sessions=2
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/scripts/migrate_json_sessions_to_mysql.py
git commit -m "chore: add JSON to MySQL session migration script"
```

## Task 6: Frontend Payload Cleanup

**Files:**

- Modify: `front/agent_web_ui/src/stores/chat.js`

- [ ] **Step 1: Stop sending `user_id` for session list**

Change:

```javascript
body: JSON.stringify({ user_id: auth.username })
```

To:

```javascript
body: JSON.stringify({})
```

- [ ] **Step 2: Keep `context.user_id` during compatibility period**

`/api/query` can keep sending `context.user_id` until backend request schema is redesigned. Backend must still prefer token identity.

- [ ] **Step 3: Stop sending `user_id` for delete**

Change:

```javascript
body: JSON.stringify({ user_id: auth.username, session_id: sessionId })
```

To:

```javascript
body: JSON.stringify({ session_id: sessionId })
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd front\agent_web_ui
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add front/agent_web_ui/src/stores/chat.js
git commit -m "refactor: rely on JWT identity for session API calls"
```

## Acceptance Criteria

- Chat sessions are stored in MySQL, not new JSON files.
- Existing API response shape remains compatible with current UI.
- Users cannot read or delete other users' sessions.
- Multi-turn context still works and includes only recent turns.
- Migration script imports existing JSON sessions without duplicating rows.
- `pytest backend/app/tests/test_conversation_service.py -v` passes.
- `pytest backend/app/tests/test_session_api_authz.py -v` passes.
- `npm run build` passes for `front/agent_web_ui`.

## Resume Bullet

> Replaced file-based chat memory with MySQL-backed conversation persistence, including session ownership, message history truncation, migration tooling, and authorization-safe session APIs.
