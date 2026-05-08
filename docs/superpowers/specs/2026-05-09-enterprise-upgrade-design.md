# ITS Multi-Agent Enterprise Upgrade Design

## Purpose

This document defines the next enterprise-grade upgrade path for the ITS Multi-Agent intelligent customer service system. The goal is to make the project stronger as a resume project and closer to a production engineering system, not merely a model API demo.

The upgrade is split into five independently implementable workstreams:

1. Database-backed conversation and event persistence
2. Security, authentication, authorization, and upload hardening
3. RAG knowledge governance and evaluation platform
4. Agent tool-call governance, resilience, and auditability
5. CI/CD, testing, quality gates, and developer operations

Each workstream has a separate implementation plan under `docs/superpowers/plans/`.

## Current Baseline

The current project already contains useful foundations:

- FastAPI main service in `backend/app`, with JWT auth, SSE streaming, OpenAI Agents SDK orchestration, local session JSON files, MySQL user table, Langfuse hooks, and local/MCP tools.
- FastAPI knowledge service in `backend/knowledge`, with document upload, Chroma vector store, HyDE, BM25, vector retrieval, title retrieval, reranking, and answer generation.
- Vue 3 agent chat UI in `front/agent_web_ui`, with Pinia auth/chat stores and SSE parsing.
- Vue 3 knowledge UI in `front/knowlege_platform_ui`, with upload and query workflows.
- Docker Compose stack for MySQL, Langfuse, backend, knowledge service, frontends, and Nginx.

The main gaps are production-readiness gaps:

- Conversations are file-based JSON instead of normalized durable data.
- Authorization is incomplete at the resource level.
- Knowledge documents are not governed as first-class records.
- Tool calls are not consistently audited, timed out, retried, or rate-limited.
- Testing, migrations, CI, and quality gates are thin.

## Enterprise Upgrade Principles

### Keep The System Understandable

The project should remain explainable in an interview. Each upgrade should map to a clear enterprise problem:

- Persistence: "How do you store and audit conversations?"
- Security: "How do you prevent data leakage between users?"
- RAG governance: "How do you know which documents produced the answer?"
- Tool governance: "How do you control unreliable external tools?"
- CI/CD: "How do you keep changes safe?"

### Prefer Incremental Delivery

The five workstreams should be implemented separately. Each one should leave the project runnable and testable.

Recommended order:

1. CI/CD and test harness, because later changes need verification.
2. Database-backed sessions, because security and observability depend on durable records.
3. Security hardening, because resource-level auth needs persisted ownership.
4. RAG governance, because document metadata and evaluation become visible product features.
5. Agent tool governance, because tool events can reuse the same event/audit model.

If speed matters more than correctness, implement database-backed sessions first because it produces the most visible resume improvement.

## Target Architecture

```text
Vue Agent UI
  |
  | JWT + SSE
  v
FastAPI Main App
  |
  | Auth dependency
  v
Conversation Service
  |-- MySQL: chat_sessions
  |-- MySQL: chat_messages
  |-- MySQL: agent_events
  |-- MySQL: tool_call_logs
  |
  v
OpenAI Agents Orchestrator
  |-- Technical Expert
  |     |-- Knowledge Tool -> Knowledge Service
  |     |-- Web Search MCP
  |-- Service Expert
  |     |-- Repair Shop DB
  |     |-- Baidu Map MCP
  |-- After-Sales Expert
        |-- Mock or future business adapters

Knowledge Service
  |-- MySQL: knowledge_documents
  |-- MySQL: knowledge_document_chunks
  |-- Chroma: embeddings
  |-- RAG evaluation endpoints
```

## Workstream 1: Database-Backed Conversation And Event Persistence

### Problem

Current session memory is stored in `backend/app/user_memories/{user_id}/{session_id}.json`. This is simple, but it is not production-grade:

- No relational ownership checks
- Hard to query, paginate, search, or audit
- No tool-call/event history
- No migration path for schema changes
- File-path user input can become a security boundary risk

### Target

Move session storage to MySQL while keeping the public API behavior stable for the frontend.

### Data Model

Add four tables:

- `chat_sessions`: one row per conversation
- `chat_messages`: one row per user/assistant/system message
- `agent_events`: streaming process events, agent switches, and reasoning/process chunks
- `tool_call_logs`: tool calls, arguments, outputs, status, duration

The application should still support:

- Creating a new session
- Listing sessions by user
- Loading visible history
- Deleting a session
- Preparing last N turns for Agent input
- Saving assistant final answer

### Design Notes

Keep `SessionService` as the business entry point. Replace or wrap `SessionRepository` with a DB implementation. Avoid leaking SQL details to API routers or agent code.

Provide a transitional migration script from JSON files to DB records. This lets existing sample data survive the upgrade.

## Workstream 2: Security, Authentication, Authorization, And Upload Hardening

### Problem

The project has JWT login/refresh foundations, but resource-level authorization and input hardening need work:

- Request body `user_id` can diverge from JWT identity.
- Access to session APIs should be based on token identity, not frontend-supplied user ID.
- Refresh tokens are stateless and cannot be revoked.
- Default secrets and API keys risk leakage.
- File upload validation is not strict enough.
- Frontend renders model output with `v-html`.

### Target

Make authentication and authorization defensible in an enterprise interview:

- Token subject is the source of truth for user identity.
- Users can only access their own sessions.
- Refresh tokens can be revoked.
- Secrets live only in `.env`.
- Uploads have type, size, path, and content validation.
- Markdown rendering is sanitized.

### Design Notes

Keep the current login UX and routes mostly stable. Tighten backend dependencies first, then simplify frontend payloads so it stops sending `user_id` where the token already contains identity.

## Workstream 3: RAG Knowledge Governance And Evaluation Platform

### Problem

The RAG pipeline is strong technically, but the platform lacks enterprise knowledge-management behavior:

- Uploads are not tracked as managed document records.
- Duplicate document handling is incomplete.
- There is no document status model.
- Deleting or replacing a document cannot reliably clean vectors.
- Answers do not expose source citations cleanly.
- Evaluation exists but is not integrated into an operator workflow.

### Target

Turn RAG from a retrieval script into a manageable knowledge platform:

- Document registry in MySQL
- Hash-based deduplication
- Ingestion status lifecycle
- Chunk metadata and vector IDs
- Source citations in query responses
- Document delete/reindex endpoints
- RAG evaluation endpoint and result persistence

### Design Notes

Do not rewrite the retrieval algorithm. Keep HyDE + BM25 + vector + title + reranker. The upgrade should add governance around the pipeline: metadata, state, traceability, and UI visibility.

## Workstream 4: Agent Tool-Call Governance, Resilience, And Auditability

### Problem

Agent tools are currently callable, but production systems need guardrails:

- Tool calls need timeout boundaries.
- Transient external failures should retry predictably.
- Tool arguments and outputs should be logged safely.
- Slow or failing tools should degrade gracefully.
- Tool usage should be observable by session.
- The orchestrator should be testable for routing quality.

### Target

Introduce a tool execution wrapper that all local tools and Agent-as-tool calls pass through:

- Timeout
- Retry with limited attempts
- Error normalization
- Structured audit log
- Optional fallback message
- Duration and status tracking

### Design Notes

Start with the three Agent-as-tool functions in `agent_factory.py`, then expand to local tools. Do not over-engineer a generic plugin framework. A small wrapper and clear log table are enough.

## Workstream 5: CI/CD, Testing, Quality Gates, And Developer Operations

### Problem

The project has many moving pieces but lacks a repeatable safety net:

- No clear backend test command
- No lint/type-check standard
- No migration workflow
- Frontend has build scripts but no CI gate
- Docker builds are not automatically validated
- Environment examples are incomplete

### Target

Create a professional project workflow:

- Backend unit tests and API tests
- Frontend build checks
- Ruff formatting/linting
- Optional mypy type checking for new modules
- GitHub Actions workflow
- `.env.example` files
- Alembic migrations for MySQL
- Seed scripts for demo data

### Design Notes

CI should avoid external paid model calls by default. Tests that require LLMs or MCP servers should be marked as integration tests and skipped in normal CI unless explicit env flags are set.

## Cross-Cutting Data And Error Handling Rules

### API Response Rules

Existing public response shapes should stay stable where possible. New endpoints should use:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

For streaming responses, keep the current `StreamPacket` envelope.

### Logging Rules

Do not log full secrets, JWTs, or raw passwords. Tool arguments may be logged only after redaction. File names should be logged, but not full uploaded content.

### Testing Rules

Every workstream needs:

- Unit tests for pure logic
- Repository/service tests for DB behavior
- API tests for auth and response contracts
- At least one negative test

External LLM, MCP, and embedding calls should be mocked in default tests.

## Resume Framing

After implementing these workstreams, the resume can honestly say:

> Built an enterprise-style multi-agent customer service platform with JWT authentication, resource-level authorization, SSE streaming, MySQL-backed conversation persistence, auditable Agent tool calls, governed RAG knowledge ingestion, hybrid retrieval with reranking, RAG evaluation, Langfuse observability, Docker deployment, and CI quality gates.

Interview-ready highlights:

- Multi-Agent architecture: Orchestrator + domain experts + tool governance
- RAG engineering: HyDE, BM25, vector retrieval, title retrieval, reranking, citations, evaluation
- Backend engineering: FastAPI, JWT, MySQL, migrations, SSE streaming
- Platform engineering: Docker Compose, Nginx, CI, test strategy, observability
- Security: user isolation, upload hardening, token lifecycle, frontend sanitization

## Implementation Documents

- `docs/superpowers/plans/2026-05-09-session-persistence.md`
- `docs/superpowers/plans/2026-05-09-security-hardening.md`
- `docs/superpowers/plans/2026-05-09-rag-knowledge-governance.md`
- `docs/superpowers/plans/2026-05-09-agent-tool-governance.md`
- `docs/superpowers/plans/2026-05-09-ci-quality-devops.md`

## Out Of Scope

These are intentionally excluded from the current upgrade batch:

- Real payment/order system integration
- Fine-tuning or training models
- Kubernetes deployment
- Multi-tenant organization billing
- Full admin RBAC beyond user-owned resources
- Replacing Chroma with a distributed vector database

