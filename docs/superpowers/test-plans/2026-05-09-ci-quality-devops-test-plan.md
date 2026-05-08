# CI Quality And Developer Operations Test Plan

## Related Implementation Plan

`docs/superpowers/plans/2026-05-09-ci-quality-devops.md`

## Test Objective

Verify that the project has repeatable local and CI quality gates: backend tests, frontend builds, lint checks, Docker Compose validation, environment examples, migration discipline, and integration-test isolation.

## Test Scope

In scope:

- `pyproject.toml`
- pytest configuration and markers
- ruff configuration
- local CI helper scripts
- GitHub Actions workflow
- frontend `check` scripts
- `.env.example` files
- Docker Compose config validation
- `.gitignore` generated artifact rules
- migration README documents

Out of scope:

- Actual GitHub-hosted run flakiness caused by third-party outages
- External model integration tests

## Test Environment

Local:

- Python 3.10
- Node 18
- Docker Desktop or Docker Engine
- PowerShell

Commands:

```powershell
ruff check backend\app backend\knowledge
pytest backend\app\tests -m "not integration" -v
pytest backend\knowledge\tests -m "not integration" -v
cd front\agent_web_ui; npm run build
cd ..\knowlege_platform_ui; npm run build
docker compose config
```

## Automated Test Cases

### CI-CONFIG-001: Pytest Discovers Both Test Roots

Type: tooling test

Steps:

1. Run:

```powershell
pytest --collect-only
```

Expected:

- Tests under `backend/app/tests` are collected.
- Tests under `backend/knowledge/tests` are collected.
- No import error caused by missing test env variables.

### CI-CONFIG-002: Integration Marker Is Registered

Type: tooling test

Steps:

1. Run:

```powershell
pytest --markers
```

Expected:

- Output includes `integration: tests that require external services, models, MCP, or network access`.

### CI-CONFIG-003: Non-Integration Tests Exclude Integration Tests

Type: tooling test

Setup:

Add or use an existing test marked:

```python
@pytest.mark.integration
def test_external_model_call():
    assert True
```

Steps:

```powershell
pytest -m "not integration" --collect-only
```

Expected:

- Integration-marked test is not selected.

### CI-LINT-001: Ruff Check Runs

Type: tooling test

Steps:

```powershell
ruff check backend\app backend\knowledge
```

Expected:

- Exit code 0 after implementation cleanup.
- If legacy files are excluded, exclusions are documented in `docs/development.md`.

### CI-APP-001: Backend App Smoke Tests Pass

Type: automated test

Steps:

```powershell
cd backend\app
pytest tests\test_health_imports.py -v
```

Expected:

- App settings import.
- Auth router import.
- No external network call.

### CI-KB-001: Knowledge Service Smoke Tests Pass

Type: automated test

Steps:

```powershell
cd backend\knowledge
pytest tests\test_health_imports.py -v
```

Expected:

- Knowledge settings import.
- Schema import.
- No embedding/model download.

### CI-FE-001: Agent UI Check Script Builds

Type: frontend build test

Steps:

```powershell
cd front\agent_web_ui
npm run check
```

Expected:

- Vite build succeeds.
- `dist/` is generated locally and ignored by git.

### CI-FE-002: Knowledge UI Check Script Builds

Type: frontend build test

Steps:

```powershell
cd front\knowlege_platform_ui
npm run check
```

Expected:

- Vite build succeeds.

### CI-SCRIPT-001: Backend App CI Script Runs

Type: local script test

Steps:

```powershell
.\scripts\ci_backend_app.ps1
```

Expected:

- Dependencies install.
- Ruff runs.
- Non-integration tests run.
- Script exits non-zero on failure.

### CI-SCRIPT-002: Knowledge CI Script Runs

Type: local script test

Steps:

```powershell
.\scripts\ci_backend_knowledge.ps1
```

Expected:

- Dependencies install.
- Ruff runs.
- Non-integration tests run.
- Script exits non-zero on failure.

### CI-SCRIPT-003: Frontend CI Script Runs

Type: local script test

Steps:

```powershell
.\scripts\ci_frontend.ps1
```

Expected:

- `npm ci` runs in both frontend projects.
- `npm run build` succeeds in both projects.

### CI-GHA-001: GitHub Actions YAML Is Valid

Type: static test

Steps:

1. Open `.github/workflows/ci.yml`.
2. Validate required jobs exist:
   - `backend-app`
   - `backend-knowledge`
   - `frontend`
   - `docker-config`

Expected:

- Workflow triggers on push and pull request to `main`.
- Each job checks out repo.
- Python jobs use Python 3.10.
- Frontend job uses Node 18.

### CI-DOCKER-001: Docker Compose Config Validates

Type: Docker config test

Steps:

```powershell
docker compose config
```

Expected:

- Exit code 0.
- Rendered config includes:
  - `backend`
  - `knowledge`
  - `agent-web-ui`
  - `knowledge-ui`
  - `nginx-proxy`
  - `mysql`
  - `langfuse-server`

### CI-DOCKER-002: Docker Healthchecks Are Present

Type: static config test

Steps:

1. Inspect `docker-compose.yml`.

Expected:

- `backend` has healthcheck.
- `knowledge` has healthcheck.
- MySQL keeps existing healthcheck.

### CI-ENV-001: Env Examples Contain Placeholders Only

Type: static test

Command:

```powershell
rg -n "sk-|real|prod|secret-value" backend\app\.env.example backend\knowledge\.env.example
```

Expected:

- No real secrets.
- Placeholder names are clear.

### CI-GITIGNORE-001: Generated Artifacts Are Ignored

Type: static/manual test

Steps:

1. Create local dummy files:
   - `backend/app/logs/app.log`
   - `backend/knowledge/chroma_kb1/dummy`
   - `front/agent_web_ui/dist/dummy`
2. Run `git status --short`.

Expected:

- Dummy generated files do not appear.
- `.env.example` remains trackable.
- `docs/superpowers/specs`, `plans`, and `test-plans` remain trackable.

### CI-MIG-001: Migration Policy Docs Exist

Type: static test

Steps:

1. Check:
   - `backend/app/migrations/README.md`
   - `backend/knowledge/migrations/README.md`

Expected:

- Both files exist.
- Both define naming convention.
- Both state old migrations should not be edited.

## Manual GitHub Verification

### CI-GHA-002: Pull Request Runs CI

Steps:

1. Push branch to GitHub.
2. Open PR to `main`.
3. Watch Actions tab.

Expected:

- All four jobs start.
- No job requires real model keys.
- Failed lint/test clearly reports file and line.

## Failure Handling Expectations

If CI fails:

- Backend test failure should show pytest assertion.
- Ruff failure should show file path and rule.
- Frontend build failure should show Vite error.
- Docker config failure should show invalid YAML/config message.

## Acceptance Gate

The feature passes when:

- Local helper scripts run successfully.
- GitHub Actions workflow is syntactically valid.
- Backend non-integration tests do not require external network.
- Frontend check scripts pass.
- Docker Compose config validates.
- Env examples and migration docs exist.
- Generated artifacts are ignored.

