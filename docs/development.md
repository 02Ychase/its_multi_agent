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

## Linting

```powershell
ruff check backend\app\services backend\app\repositories backend\knowledge\services backend\knowledge\repositories
```

Note: Legacy modules outside `services/` and `repositories/` directories may have existing lint issues. CI scope is currently narrowed to these directories for new code quality enforcement.

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

## Migrations

Store SQL migrations in the appropriate `migrations/` directory:

- `backend/app/migrations/` - App database tables
- `backend/knowledge/migrations/` - Knowledge service tables

Naming convention: `YYYYMMDDHHMM_description.sql`
