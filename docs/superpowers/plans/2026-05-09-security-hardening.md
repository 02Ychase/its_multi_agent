# Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade authentication, authorization, secret handling, upload validation, and frontend rendering safety so the project has defensible enterprise security boundaries.

**Architecture:** Treat JWT identity as the source of truth, add refresh-token persistence and revocation, move secrets into environment examples, enforce upload constraints in the knowledge service, and sanitize all frontend-rendered Markdown/HTML. Security checks live in backend dependencies and service-layer utilities, not scattered through UI code.

**Tech Stack:** FastAPI dependencies, python-jose, passlib/bcrypt, MySQL, Vue 3, DOMPurify, pytest.

---

## File Map

Create:

- `backend/app/models/refresh_token.py`
- `backend/app/services/security_service.py`
- `backend/app/tests/test_auth_security.py`
- `backend/knowledge/services/upload_validation.py`
- `backend/knowledge/tests/test_upload_validation.py`
- `backend/app/.env.example`
- `backend/knowledge/.env.example`

Modify:

- `backend/app/config/settings.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/auth_router.py`
- `backend/app/api/routers.py`
- `backend/knowledge/api/routers.py`
- `front/agent_web_ui/package.json`
- `front/agent_web_ui/src/components/ChatMessage.vue`
- `front/agent_web_ui/src/components/ThinkingBlock.vue`
- `front/knowlege_platform_ui/package.json`
- `front/knowlege_platform_ui/src/views/Chat.vue`

## Security Requirements

1. A caller cannot override token identity with request-body `user_id`.
2. Refresh tokens are stored hashed, can expire, and can be revoked.
3. Logout revokes the current refresh token.
4. File uploads have extension, size, filename, and content checks.
5. Markdown output is sanitized before `v-html`.
6. No committed source file contains real API keys or production secrets.
7. CORS defaults are configurable and not always `*` in production.

## Task 1: Refresh Token Persistence

**Files:**

- Create: `backend/app/models/refresh_token.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/api/auth_router.py`
- Test: `backend/app/tests/test_auth_security.py`

- [ ] **Step 1: Add refresh token table**

Create a model module with `init_refresh_tokens_table()`:

```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    jti VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_refresh_jti (jti),
    INDEX idx_user_active (user_id, revoked_at),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Store only a SHA-256 hash of the refresh token string:

```python
import hashlib

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

- [ ] **Step 2: Add token issue/revoke helpers**

`refresh_token.py` should provide these methods:

| Method | Required behavior |
| --- | --- |
| `save_refresh_token(user_id: int, token: str, jti: str, expires_at: datetime) -> None` | Hash the token and insert one active refresh-token row. |
| `is_refresh_token_active(token: str, jti: str) -> bool` | Return `True` only when hash and `jti` match, `revoked_at` is null, and `expires_at` is in the future. |
| `revoke_refresh_token(token: str, jti: str) -> bool` | Mark the matching token as revoked and return whether a row changed. |
| `revoke_all_user_refresh_tokens(user_id: int) -> int` | Revoke every active refresh token for the user and return affected row count. |

- [ ] **Step 3: Include `jti` in refresh JWT**

Update `create_refresh_token()`:

```python
import uuid

jti = str(uuid.uuid4())
to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
save_refresh_token(data["user_id"], token, jti, expire.replace(tzinfo=None))
return token
```

- [ ] **Step 4: Validate refresh token against DB**

`refresh_access_token()` must decode JWT, check `type == "refresh"`, then call `is_refresh_token_active(refresh_token, payload["jti"])`.

- [ ] **Step 5: Add logout route**

Add:

```python
class LogoutRequest(BaseModel):
    refresh_token: str

@router.post("/logout", summary="退出登录")
async def logout(request: LogoutRequest):
    payload = decode_token(request.refresh_token)
    if payload and payload.get("type") == "refresh":
        revoke_refresh_token(request.refresh_token, payload.get("jti", ""))
    return {"success": True}
```

- [ ] **Step 6: Tests**

Add tests for:

- Refresh succeeds before revocation.
- Refresh fails after logout.
- Refresh fails for unknown token.
- Expired token fails.

Run:

```powershell
cd backend\app
pytest tests\test_auth_security.py -v
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/models/refresh_token.py backend/app/services/auth_service.py backend/app/api/auth_router.py backend/app/tests/test_auth_security.py
git commit -m "feat: persist and revoke refresh tokens"
```

## Task 2: Resource-Level Authorization

**Files:**

- Create: `backend/app/services/security_service.py`
- Modify: `backend/app/api/routers.py`
- Test: `backend/app/tests/test_auth_security.py`

- [ ] **Step 1: Add identity helper**

Create:

```python
def require_current_user_id(current_user: dict) -> int:
    user_id = current_user.get("user_id")
    if not isinstance(user_id, int):
        try:
            return int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="无效用户身份")
    return user_id
```

- [ ] **Step 2: Ignore request-body user_id**

In `/api/user_sessions`, `/api/delete_session`, and `/api/query`, use JWT identity. If `request.context.user_id` is needed for compatibility, treat it only as display metadata.

- [ ] **Step 3: Add mismatch warning**

If request body contains a different `user_id`, log a warning:

```python
logger.warning("Request user_id ignored because JWT identity is authoritative")
```

Do not return another user's data.

- [ ] **Step 4: Tests**

Add tests:

- User A sends payload `{user_id: "userB"}` and still receives User A sessions.
- User A cannot delete User B session.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/security_service.py backend/app/api/routers.py backend/app/tests/test_auth_security.py
git commit -m "fix: enforce resource ownership from JWT identity"
```

## Task 3: Secret And CORS Hardening

**Files:**

- Modify: `backend/app/config/settings.py`
- Create: `backend/app/.env.example`
- Create: `backend/knowledge/.env.example`
- Modify: `backend/app/api/main.py`

- [ ] **Step 1: Remove default real API key values**

Change any default API key value to `None`. In particular, `DASHSCOPE_API_KEY` must not default to a real key.

Use:

```python
DASHSCOPE_API_KEY: Optional[str] = Field(default=None)
```

- [ ] **Step 2: Add configurable CORS origins**

Add setting:

```python
CORS_ALLOW_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000")
```

In `api/main.py`:

```python
origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
allow_origins=origins
```

- [ ] **Step 3: Add `.env.example` files**

`backend/app/.env.example` should include placeholder values:

```text
MAIN_API_KEY=
MAIN_BASE_URL=
MAIN_MODEL_NAME=MiMo-V2.5-Pro
SUB_API_KEY=
SUB_BASE_URL=
SUB_MODEL_NAME=MiniMax-m2.7
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=its_db
KNOWLEDGE_BASE_URL=http://127.0.0.1:8001
DASHSCOPE_BASE_URL=
DASHSCOPE_API_KEY=
BAIDUMAP_AK=
JWT_SECRET_KEY=replace-with-a-long-random-secret
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
```

`backend/knowledge/.env.example`:

```text
API_KEY=
BASE_URL=
MODEL=
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
HYDE_ENABLED=true
RERANKER_ENABLED=true
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/config/settings.py backend/app/api/main.py backend/app/.env.example backend/knowledge/.env.example
git commit -m "chore: remove default secrets and configure CORS origins"
```

## Task 4: Knowledge Upload Validation

**Files:**

- Create: `backend/knowledge/services/upload_validation.py`
- Modify: `backend/knowledge/config/settings.py`
- Modify: `backend/knowledge/api/routers.py`
- Test: `backend/knowledge/tests/test_upload_validation.py`

- [ ] **Step 1: Add settings**

```python
MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024
UPLOAD_ALLOWED_EXTENSIONS: str = ".md,.txt,.docx,.pdf"
```

- [ ] **Step 2: Create validator**

Validator responsibilities:

Create these validator functions:

| Function | Required behavior |
| --- | --- |
| `sanitize_filename(filename: str) -> str` | Strip path separators, control characters, reserved Windows names, and leading/trailing whitespace; return a safe basename. |
| `validate_upload_extension(filename: str) -> str` | Return the lowercase extension when it is allowed; raise `ValueError` otherwise. |
| `validate_upload_size(size_bytes: int) -> None` | Raise `ValueError` when the file exceeds `settings.MAX_UPLOAD_BYTES`. |
| `validate_safe_temp_path(base_dir: str, target_path: str) -> None` | Resolve both paths and raise `ValueError` unless `target_path` stays under `base_dir`. |

Rules:

- Reject names containing `/`, `\`, `..`, or empty basename.
- Reject files larger than `MAX_UPLOAD_BYTES`.
- Only allow configured extensions.
- Use sanitized file name when building paths.

- [ ] **Step 3: Apply in upload route**

In `upload_file()`:

- Validate extension before reading.
- Count bytes while reading.
- Use sanitized filename for temp and permanent paths.
- Fix the current cleanup logic so it does not check the moved-away temp path before copying to permanent storage.

- [ ] **Step 4: Tests**

Cases:

- `../../evil.md` is rejected or sanitized to `evil.md`.
- `.exe` is rejected.
- Oversized file is rejected.
- Valid `.md` passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/knowledge/services/upload_validation.py backend/knowledge/config/settings.py backend/knowledge/api/routers.py backend/knowledge/tests/test_upload_validation.py
git commit -m "fix: harden knowledge file upload validation"
```

## Task 5: Frontend Markdown Sanitization

**Files:**

- Modify: `front/agent_web_ui/package.json`
- Modify: `front/agent_web_ui/src/components/ChatMessage.vue`
- Modify: `front/agent_web_ui/src/components/ThinkingBlock.vue`
- Modify: `front/knowlege_platform_ui/package.json`
- Modify: `front/knowlege_platform_ui/src/views/Chat.vue`

- [ ] **Step 1: Add DOMPurify**

Run:

```powershell
cd front\agent_web_ui
npm install dompurify
cd ..\knowlege_platform_ui
npm install dompurify
```

- [ ] **Step 2: Sanitize rendered Markdown**

Use:

```javascript
import DOMPurify from 'dompurify'

const renderedContent = computed(() => {
  if (!props.message?.content) return ''
  try {
    return DOMPurify.sanitize(marked.parse(props.message.content))
  } catch {
    return DOMPurify.sanitize(props.message.content)
  }
})
```

Apply the same pattern to `ThinkingBlock.vue` and `front/knowlege_platform_ui/src/views/Chat.vue`.

- [ ] **Step 3: Build both frontends**

```powershell
cd front\agent_web_ui
npm run build
cd ..\knowlege_platform_ui
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add front/agent_web_ui/package.json front/agent_web_ui/package-lock.json front/agent_web_ui/src/components/ChatMessage.vue front/agent_web_ui/src/components/ThinkingBlock.vue front/knowlege_platform_ui/package.json front/knowlege_platform_ui/package-lock.json front/knowlege_platform_ui/src/views/Chat.vue
git commit -m "fix: sanitize markdown HTML rendering in frontends"
```

## Acceptance Criteria

- Refresh token can be revoked and cannot be reused after logout.
- APIs use JWT identity for ownership checks.
- No source file contains hardcoded real API keys.
- CORS is configurable from `.env`.
- Unsafe uploads are rejected.
- Markdown rendering is sanitized before `v-html`.
- Backend auth/security tests pass.
- Knowledge upload validation tests pass.
- Both frontend builds pass.

## Resume Bullet

> Hardened a FastAPI/Vue multi-agent platform with JWT resource-level authorization, refresh-token revocation, upload validation, secret externalization, configurable CORS, and XSS-safe Markdown rendering.
