# CI Quality And Developer Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repeatable tests, linting, formatting, migration discipline, environment examples, Docker validation, and GitHub Actions so the project has a professional engineering workflow.

**Architecture:** Establish lightweight quality gates that avoid external LLM/MCP calls by default. Unit and API tests mock external services. Integration tests are opt-in. CI runs backend lint/tests, frontend builds, and Docker Compose config validation on every pull request.

**Tech Stack:** pytest, pytest-asyncio, ruff, optional mypy, npm/Vite build, Docker Compose, GitHub Actions, Alembic or SQL migration scripts.

---

## File Map

Create:

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `backend/app/tests/conftest.py`
- `backend/knowledge/tests/conftest.py`
- `backend/app/tests/test_health_imports.py`
- `backend/knowledge/tests/test_health_imports.py`
- `backend/app/.env.example`
- `backend/knowledge/.env.example`
- `docs/development.md`
- `scripts/ci_backend_app.ps1`
- `scripts/ci_backend_knowledge.ps1`
- `scripts/ci_frontend.ps1`

Modify:

- `backend/app/requirements.txt`
- `backend/knowledge/requirements.txt`
- `front/agent_web_ui/package.json`
- `front/knowlege_platform_ui/package.json`
- `docker-compose.yml`
- `.gitignore`

## CI Strategy

Default CI should run without paid APIs:

- Import checks
- Unit tests
- API contract tests with mocks
- Frontend builds
- Docker Compose config validation

Default CI should not run:

- Real LLM calls
- Real embedding calls
- Real MCP calls
- RAGAS evaluation against online models
- Reranker model download

Mark these as integration tests and require explicit env flag:

```python
@pytest.mark.integration
```

## Task 1: Python Tooling Configuration

**Files:**

- Create: `pyproject.toml`
- Modify: `backend/app/requirements.txt`
- Modify: `backend/knowledge/requirements.txt`

- [ ] **Step 1: Add test/lint dependencies**

Append to both backend requirements:

```text
pytest>=8.0.0
pytest-asyncio>=0.23.0
ruff>=0.6.0
```

If mypy is desired for new modules:

```text
mypy>=1.10.0
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = [
  "backend/app/tests",
  "backend/knowledge/tests"
]
asyncio_mode = "auto"
markers = [
  "integration: tests that require external services, models, MCP, or network access"
]

[tool.ruff]
line-length = 120
target-version = "py310"
extend-exclude = [
  "backend/knowledge/data",
  "backend/knowledge/chroma_kb1",
  "backend/app/user_memories",
  "front",
  "docs"
]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = [
  "E501"
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 3: Run lint check**

```powershell
ruff check backend\app backend\knowledge
```

If the current code has many legacy lint issues, narrow CI to new modules first:

```powershell
ruff check backend\app\services backend\app\repositories backend\knowledge\services backend\knowledge\repositories
```

Document the chosen scope in `docs/development.md`.

- [ ] **Step 4: Commit**

```powershell
git add pyproject.toml backend/app/requirements.txt backend/knowledge/requirements.txt
git commit -m "chore: add pytest and ruff tooling configuration"
```

## Task 2: Test Fixtures And Import Smoke Tests

**Files:**

- Create: `backend/app/tests/conftest.py`
- Create: `backend/knowledge/tests/conftest.py`
- Create: `backend/app/tests/test_health_imports.py`
- Create: `backend/knowledge/tests/test_health_imports.py`

- [ ] **Step 1: Backend app test env fixture**

`backend/app/tests/conftest.py`:

```python
import os
import pytest

@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("MAIN_API_KEY", "test")
    monkeypatch.setenv("MAIN_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("SUB_API_KEY", "test")
    monkeypatch.setenv("SUB_BASE_URL", "http://test.local/v1")
    monkeypatch.setenv("MYSQL_HOST", os.getenv("MYSQL_HOST", "localhost"))
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-for-ci")
```

- [ ] **Step 2: Knowledge test env fixture**

`backend/knowledge/tests/conftest.py`:

```python
import pytest

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
```

- [ ] **Step 3: Add import tests**

`backend/app/tests/test_health_imports.py`:

```python
def test_app_settings_imports():
    from config.settings import settings
    assert settings.JWT_ALGORITHM == "HS256"

def test_auth_router_imports():
    from api.auth_router import router
    assert router.prefix == "/api/auth"
```

`backend/knowledge/tests/test_health_imports.py`:

```python
def test_knowledge_settings_imports():
    from config.settings import settings
    assert settings.CHUNK_OVERLAP == 200

def test_schema_imports():
    from schemas.schema import QueryRequest
    assert QueryRequest(question="x").question == "x"
```

- [ ] **Step 4: Run tests**

```powershell
pytest backend\app\tests\test_health_imports.py backend\knowledge\tests\test_health_imports.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/tests/conftest.py backend/knowledge/tests/conftest.py backend/app/tests/test_health_imports.py backend/knowledge/tests/test_health_imports.py
git commit -m "test: add backend import smoke tests"
```

## Task 3: CI Helper Scripts

**Files:**

- Create: `scripts/ci_backend_app.ps1`
- Create: `scripts/ci_backend_knowledge.ps1`
- Create: `scripts/ci_frontend.ps1`

- [ ] **Step 1: Backend app CI script**

```powershell
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend\app"
python -m pip install -r requirements.txt
ruff check .
pytest tests -m "not integration" -v
```

- [ ] **Step 2: Knowledge CI script**

```powershell
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend\knowledge"
python -m pip install -r requirements.txt
ruff check .
pytest tests -m "not integration" -v
```

- [ ] **Step 3: Frontend CI script**

```powershell
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\front\agent_web_ui"
npm ci
npm run build
Set-Location "$PSScriptRoot\..\front\knowlege_platform_ui"
npm ci
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add scripts/ci_backend_app.ps1 scripts/ci_backend_knowledge.ps1 scripts/ci_frontend.ps1
git commit -m "chore: add local CI helper scripts"
```

## Task 4: Frontend Quality Scripts

**Files:**

- Modify: `front/agent_web_ui/package.json`
- Modify: `front/knowlege_platform_ui/package.json`

- [ ] **Step 1: Add check script**

Add:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "check": "vite build"
}
```

This keeps the current stack simple without adding ESLint immediately.

- [ ] **Step 2: Verify builds**

```powershell
cd front\agent_web_ui
npm run check
cd ..\knowlege_platform_ui
npm run check
```

- [ ] **Step 3: Commit**

```powershell
git add front/agent_web_ui/package.json front/agent_web_ui/package-lock.json front/knowlege_platform_ui/package.json front/knowlege_platform_ui/package-lock.json
git commit -m "chore: add frontend check scripts"
```

## Task 5: GitHub Actions Workflow

**Files:**

- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create workflow**

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  backend-app:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install backend app dependencies
        working-directory: backend/app
        run: python -m pip install -r requirements.txt
      - name: Ruff backend app
        working-directory: backend/app
        run: ruff check .
      - name: Test backend app
        working-directory: backend/app
        env:
          MAIN_API_KEY: test
          MAIN_BASE_URL: http://test.local/v1
          SUB_API_KEY: test
          SUB_BASE_URL: http://test.local/v1
          JWT_SECRET_KEY: test-secret-for-ci
        run: pytest tests -m "not integration" -v

  backend-knowledge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install knowledge dependencies
        working-directory: backend/knowledge
        run: python -m pip install -r requirements.txt
      - name: Ruff knowledge
        working-directory: backend/knowledge
        run: ruff check .
      - name: Test knowledge
        working-directory: backend/knowledge
        env:
          API_KEY: test
          BASE_URL: http://test.local/v1
          MODEL: test-model
          EMBEDDING_API_KEY: test
          EMBEDDING_BASE_URL: http://test.local/v1
          EMBEDDING_MODEL: test-embedding
          HYDE_ENABLED: "false"
          RERANKER_ENABLED: "false"
        run: pytest tests -m "not integration" -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "18"
      - name: Build agent web UI
        working-directory: front/agent_web_ui
        run: |
          npm ci
          npm run build
      - name: Build knowledge platform UI
        working-directory: front/knowlege_platform_ui
        run: |
          npm ci
          npm run build

  docker-config:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Docker Compose config
        run: docker compose config
```

- [ ] **Step 2: Commit**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: add backend frontend and docker validation workflow"
```

## Task 6: Environment Examples And Development Guide

**Files:**

- Create or Modify: `backend/app/.env.example`
- Create or Modify: `backend/knowledge/.env.example`
- Create: `docs/development.md`

- [ ] **Step 1: Ensure env examples exist**

Use the examples from the security-hardening plan. They must contain placeholders only.

- [ ] **Step 2: Add development guide**

`docs/development.md` should include:

```markdown
# Development Guide

## Local Services

Run all services:

```powershell
.\start_all.bat
```

Run app backend only:

```powershell
cd backend\app
$env:PYTHONPATH=(Get-Location).Path
python -m api.main
```

Run knowledge service only:

```powershell
cd backend\knowledge
python -m api.main
```

## Tests

```powershell
pytest backend\app\tests -m "not integration" -v
pytest backend\knowledge\tests -m "not integration" -v
```

## Frontend Builds

```powershell
cd front\agent_web_ui
npm run build
cd ..\knowlege_platform_ui
npm run build
```

## Integration Tests

Integration tests may call LLMs, embeddings, MCP, or local databases. Run them only when required:

```powershell
pytest -m integration -v
```

## Docker

```powershell
docker compose up -d
docker compose logs -f backend
docker compose down
```
```

- [ ] **Step 3: Commit**

```powershell
git add backend/app/.env.example backend/knowledge/.env.example docs/development.md
git commit -m "docs: add environment examples and development guide"
```

## Task 7: Docker Build Validation

**Files:**

- Modify: `docker-compose.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Add healthchecks where useful**

Backend service:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

Knowledge service:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/docs')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

- [ ] **Step 2: Ignore generated local artifacts**

Ensure `.gitignore` includes:

```text
backend/app/logs/
backend/app/user_memories/
backend/knowledge/data/tmp/
backend/knowledge/data/uploaded/
backend/knowledge/chroma_kb1/
logs/
.env
```

Do not ignore `.env.example`.

- [ ] **Step 3: Validate compose**

```powershell
docker compose config
```

- [ ] **Step 4: Commit**

```powershell
git add docker-compose.yml .gitignore
git commit -m "chore: add compose healthchecks and ignore generated artifacts"
```

## Task 8: Migration Discipline

**Files:**

- Create: `backend/app/migrations/README.md`
- Create: `backend/knowledge/migrations/README.md`

- [ ] **Step 1: Add migration policy**

`backend/app/migrations/README.md`:

```markdown
# App Database Migrations

Store SQL migrations for app-owned tables here.

Naming:

```text
YYYYMMDDHHMM_description.sql
```

Rules:

- Migrations must be idempotent when practical.
- Do not edit old migrations after they are applied.
- Add a short rollback note in comments when destructive changes are introduced.
```

`backend/knowledge/migrations/README.md` follows the same format for knowledge service tables.

- [ ] **Step 2: Commit**

```powershell
git add backend/app/migrations/README.md backend/knowledge/migrations/README.md
git commit -m "docs: add database migration policy"
```

## Acceptance Criteria

- `pyproject.toml` configures pytest and ruff.
- Backend smoke tests run without external LLM/MCP calls.
- Frontend builds pass in CI.
- GitHub Actions workflow validates backend, frontend, and Docker Compose config.
- `.env.example` files exist and contain no real secrets.
- Development guide explains local startup, tests, integration tests, and Docker.
- Generated files and local secrets are ignored.
- Migrations have a documented policy.

## Resume Bullet

> Built a CI/CD and quality-gate workflow for a multi-service AI platform, including pytest, ruff, frontend build validation, Docker Compose validation, environment templates, migration discipline, and integration-test isolation.

