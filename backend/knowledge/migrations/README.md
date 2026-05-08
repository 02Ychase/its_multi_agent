# Knowledge Service Database Migrations

Store SQL migrations for knowledge service tables here.

Naming:

```text
YYYYMMDDHHMM_description.sql
```

Rules:

- Migrations must be idempotent when practical.
- Do not edit old migrations after they are applied.
- Add a short rollback note in comments when destructive changes are introduced.
