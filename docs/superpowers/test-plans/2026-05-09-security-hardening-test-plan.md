# Security Hardening Test Plan

## Related Implementation Plan

`docs/superpowers/plans/2026-05-09-security-hardening.md`

## Test Objective

Verify that authentication, authorization, refresh-token lifecycle, upload validation, secret handling, CORS configuration, and frontend HTML sanitization meet enterprise-grade safety expectations.

## Test Scope

In scope:

- JWT access-token validation
- Refresh-token persistence and revocation
- Logout behavior
- Resource-level authorization
- Upload filename, extension, size, and path validation
- Secret externalization
- CORS origin configuration
- DOMPurify sanitization in both frontends

Out of scope:

- Database session behavior, covered in session persistence test plan
- Tool-call fallback behavior, covered in tool governance test plan
- Browser penetration testing beyond documented XSS cases

## Test Environment

Required:

- MySQL test database
- Backend app test server or FastAPI TestClient
- Knowledge service TestClient
- Frontend build environment

Commands:

```powershell
cd backend\app
pytest tests\test_auth_security.py -v
cd ..\knowledge
pytest tests\test_upload_validation.py -v
cd ..\..\front\agent_web_ui
npm run build
cd ..\knowlege_platform_ui
npm run build
```

## Test Data

Users:

| Username | Password | Email |
| --- | --- | --- |
| `secure_user_a` | `password123` | `secure_a@example.com` |
| `secure_user_b` | `password123` | `secure_b@example.com` |

Files:

| Filename | Content | Expected |
| --- | --- | --- |
| `valid.md` | `# Title\ncontent` | accepted |
| `evil.exe` | `binary` | rejected |
| `../../evil.md` | `# Evil` | rejected or sanitized to safe basename |
| `oversize.md` | bytes above max limit | rejected |

XSS payloads:

```html
<img src=x onerror=alert(1)>
<script>alert(1)</script>
[click](javascript:alert(1))
```

## Automated Test Cases

### SEC-AUTH-001: Register Enforces Password Length

Type: API test

Steps:

1. POST `/api/auth/register` with password `123`.

Expected:

- HTTP 400.
- Error message indicates password is too short.
- No user row is created.

### SEC-AUTH-002: Login Returns Access And Refresh Tokens

Type: API test

Steps:

1. Register `secure_user_a`.
2. POST `/api/auth/login`.

Expected:

- HTTP 200.
- Response includes:
  - `access_token`
  - `refresh_token`
  - `token_type: bearer`
  - `user.username`
- `refresh_tokens` table contains one hashed token row.
- Raw refresh token is not stored in DB.

### SEC-AUTH-003: Refresh Token Can Be Used Once Or Repeated While Active

Type: API test

Steps:

1. Login.
2. POST `/api/auth/refresh` with the refresh token.

Expected:

- HTTP 200.
- New access token returned.
- Refresh succeeds only if token exists, is not revoked, and is not expired.

### SEC-AUTH-004: Logout Revokes Refresh Token

Type: API test

Steps:

1. Login and store refresh token.
2. POST `/api/auth/logout`.
3. POST `/api/auth/refresh` with the same refresh token.

Expected:

- Logout returns success.
- Refresh after logout returns HTTP 401.
- DB row has non-null `revoked_at`.

### SEC-AUTH-005: Tampered Refresh Token Fails

Type: API test

Steps:

1. Login.
2. Modify one character in refresh token.
3. POST `/api/auth/refresh`.

Expected:

- HTTP 401.
- No new access token.
- Warning is logged without printing the token.

### SEC-AUTH-006: Access Token Protects Chat APIs

Type: API test

Endpoints:

- `/api/query`
- `/api/user_sessions`
- `/api/delete_session`

Steps:

1. Call each endpoint without token.
2. Call each endpoint with malformed token.
3. Call each endpoint with valid token.

Expected:

- Missing/malformed token returns 401.
- Valid token reaches business logic.

### SEC-AUTHZ-001: User ID In Payload Is Ignored

Type: API test

Steps:

1. Login as `secure_user_a`.
2. Send `/api/user_sessions` with body `{"user_id": "secure_user_b"}`.

Expected:

- Response contains only User A data.
- Log warns that request body identity was ignored.

### SEC-CONFIG-001: No Hardcoded Real API Key Defaults

Type: static test

Command:

```powershell
rg -n "sk-|api_key|DASHSCOPE_API_KEY.*default=.*sk" backend
```

Expected:

- No real key is present in source.
- `.env.example` contains placeholders only.

### SEC-CORS-001: CORS Uses Configured Origins

Type: unit/API test

Setup:

Set:

```text
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
```

Steps:

1. Start app.
2. Send preflight request from `http://localhost:5173`.
3. Send preflight request from `http://evil.example`.

Expected:

- Allowed origin receives `access-control-allow-origin`.
- Disallowed origin does not receive permissive allow header.

### SEC-UPLOAD-001: Valid Upload Passes

Type: knowledge API test

Steps:

1. Upload `valid.md`.

Expected:

- HTTP 200.
- Response status `success`.
- File is stored under controlled upload directory.

### SEC-UPLOAD-002: Unsupported Extension Fails

Type: knowledge API test

Steps:

1. Upload `evil.exe`.

Expected:

- HTTP 400.
- No temp or permanent file remains.
- No vector ingestion is triggered.

### SEC-UPLOAD-003: Path Traversal Filename Is Rejected Or Sanitized

Type: unit/API test

Steps:

1. Pass `../../evil.md` to `sanitize_filename()`.
2. Try uploading with path traversal filename.

Expected:

- Sanitizer returns `evil.md` or raises `ValueError`.
- Final resolved path remains under configured upload/tmp directory.
- No file is written outside project upload directories.

### SEC-UPLOAD-004: Oversized Upload Fails

Type: knowledge API test

Steps:

1. Configure `MAX_UPLOAD_BYTES=1024`.
2. Upload file with 1025 bytes.

Expected:

- HTTP 400 or 413.
- Response indicates upload is too large.
- Temp file is deleted.

### SEC-XSS-001: Agent UI Sanitizes Assistant Markdown

Type: component/manual browser test

Steps:

1. Render assistant content:

```html
<img src=x onerror=alert(1)><script>alert(1)</script>
```

2. Inspect rendered HTML.

Expected:

- `script` tag removed.
- `onerror` attribute removed.
- No alert executes.

### SEC-XSS-002: Knowledge UI Sanitizes Markdown

Type: component/manual browser test

Steps:

1. Mock query response answer with XSS payload.
2. Render in `front/knowlege_platform_ui/src/views/Chat.vue`.

Expected:

- Dangerous tags/attributes removed.
- Normal Markdown still renders.

## Manual Security Checklist

- [ ] Logout removes tokens from localStorage.
- [ ] Refresh token cannot be used after logout.
- [ ] Browser devtools show no raw secret in frontend bundle.
- [ ] Uploading invalid file shows user-friendly error.
- [ ] Backend logs do not include JWTs or passwords.

## Regression Tests

Run:

```powershell
pytest backend\app\tests -m "not integration" -v
pytest backend\knowledge\tests -m "not integration" -v
cd front\agent_web_ui; npm run build
cd ..\knowlege_platform_ui; npm run build
```

Expected:

- All tests pass.
- Both builds succeed.

## Acceptance Gate

The feature passes when:

- Token lifecycle tests pass.
- Cross-user authorization tests pass.
- Upload validation tests pass.
- Static secret scan passes.
- Frontend XSS payloads are sanitized.
- No existing login/chat flow regression is observed.

