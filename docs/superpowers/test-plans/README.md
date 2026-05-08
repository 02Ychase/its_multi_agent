# ITS Enterprise Upgrade Test Plans

This directory contains detailed test plans for the five enterprise upgrade workstreams.

## Test Plan Index

| Workstream | Test Plan | Implementation Plan |
| --- | --- | --- |
| Database-backed session persistence | `2026-05-09-session-persistence-test-plan.md` | `../plans/2026-05-09-session-persistence.md` |
| Security hardening | `2026-05-09-security-hardening-test-plan.md` | `../plans/2026-05-09-security-hardening.md` |
| RAG knowledge governance | `2026-05-09-rag-knowledge-governance-test-plan.md` | `../plans/2026-05-09-rag-knowledge-governance.md` |
| Agent tool governance | `2026-05-09-agent-tool-governance-test-plan.md` | `../plans/2026-05-09-agent-tool-governance.md` |
| CI quality and developer operations | `2026-05-09-ci-quality-devops-test-plan.md` | `../plans/2026-05-09-ci-quality-devops.md` |

## How To Use These Documents

For each workstream:

1. Read the implementation plan first.
2. Read the matching test plan.
3. Implement the first task with tests before production code where practical.
4. Run the test commands in the test plan.
5. Do not mark a workstream complete until the acceptance gate passes.

## Default Test Policy

Default test runs must avoid external paid or unstable services:

- No real LLM calls
- No real embedding calls
- No real MCP calls
- No reranker model download

Tests that require external systems must use:

```python
@pytest.mark.integration
```

and must be run explicitly:

```powershell
pytest -m integration -v
```

