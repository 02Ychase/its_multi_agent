# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ITS Multi-Agent is a Chinese-language intelligent customer service system built on a multi-agent architecture. It supports technical consultation, service station navigation, order after-sales, and knowledge base RAG retrieval.

## Commands

### Local Development

```bash
# Start all services (Windows)
start_all.bat        # Starts Knowledge (8001), Backend (8000), Agent Web UI (5173), Knowledge UI (3000)
stop.bat             # Kills all service processes

# Individual services
cd backend/app && python api/main.py              # Main backend on :8000
cd backend/knowledge && uvicorn api.main:app --port 8001  # Knowledge service on :8001
cd front/agent_web_ui && npm run dev               # Chat UI on :5173
cd front/knowlege_platform_ui && npm run dev       # Knowledge management on :3000

# Install dependencies
cd backend/app && pip install -r requirements.txt
cd backend/knowledge && pip install -r requirements.txt
cd front/agent_web_ui && npm install
cd front/knowlege_platform_ui && npm install
```

### Docker

```bash
docker-compose up -d    # 8 services: MySQL, Langfuse DB/Server, Backend, Knowledge, 2 Frontends, Nginx
```

### Frontend Build

```bash
npm run build    # In either frontend directory
npm run lint     # Not configured - no lint scripts defined
```

## Architecture

### Two Backend Services

1. **Main App** (`backend/app/`, port 8000) - FastAPI multi-agent orchestrator with JWT auth and SSE streaming
2. **Knowledge Service** (`backend/knowledge/`, port 8001) - Standalone RAG pipeline, no auth

The main app's technical agent calls the knowledge service via HTTP (`/query` endpoint) as a tool.

### Multi-Agent System (OpenAI Agents SDK)

Uses `openai-agents` package with an Agent-as-Tool pattern (not handoff):

- **Orchestrator** (`orchestrator_agent.py`) - Routes intent to sub-agents via `@function_tool` wrappers
- **Technical Expert** (`technical_agent.py`) - Knowledge base RAG + DashScope WebSearch MCP
- **Service Expert** (`service_agent.py`) - MySQL repair shop queries + Baidu Maps MCP
- **After-Sales Expert** (`after_sales_agent.py`) - Mock data for orders/warranty/repair

Sub-agents are wrapped as `@function_tool` in `agent_factory.py` and called by the orchestrator via `Runner.run()`. All agents use `sub_model`; `main_model` is defined but unused.

### RAG Pipeline (`backend/knowledge/services/retrieval_service.py`)

HyDE query rewriting -> three-way parallel retrieval (BM25 + vector + title-based) -> deduplication -> cross-encoder reranking -> top-K results.

Key: BM25 uses jieba tokenization; vector store is ChromaDB with DashScope text-embedding-v4; reranker is `bge-reranker-v2-m3`.

### SSE Streaming

`stream_response_service.py` processes `RunResultStreaming` events into SSE `data:` lines. Event types: `ResponseTextDeltaEvent` (ANSWER), reasoning deltas (THINKING), tool calls (PROCESS), agent updates (PROCESS).

### Authentication

JWT with bcrypt password hashing. Access tokens (30min) + refresh tokens (7 days). Frontend Pinia stores handle token lifecycle with `authFetch()` wrapper that auto-refreshes on 401.

### Session Storage

File-based JSON in `backend/app/user_memories/{user_id}/{session_id}.json`. Truncated to last 3 turns (6 messages).

### Two Frontend Apps

1. **agent_web_ui** (port 5173) - Vue 3 + Pinia + native fetch, SSE streaming, JWT auth
2. **knowlege_platform_ui** (port 3000) - Vue 3 + Axios, no auth, document upload + simple Q&A

Both use Element Plus for UI. Agent web UI has hardcoded API base `http://127.0.0.1:8000`; knowledge UI uses Vite proxy to port 8001.

## Configuration

- Backend config: `backend/app/.env` loaded via pydantic-settings (`backend/app/config/settings.py`)
- Knowledge config: `backend/knowledge/.env` (`backend/knowledge/config/settings.py`)
- Dual LLM setup: MAIN model (MiMo-V2.5-Pro) and SUB model (mimo-v2.5), both via Xiaomi API endpoint
- MySQL database `its_db` with users table and repair_shops table (auto-created at startup)
- MCP clients: DashScope WebSearch (StreamableHTTP) and Baidu Maps (SSE)

## Key Patterns

- Prompts are Markdown files in `backend/app/prompts/`, loaded by `prompt_loader.py`
- `@observe` decorators from Langfuse on agents, tools, and RAG for tracing
- Tool display names mapped in `text_util.py` (`TOOL_NAME_MAPPING`)
- Evaluation: LLM-as-Judge (`evaluation/judge.py`) scores 5 dimensions (0-10); RAGAS framework for RAG metrics
- Knowledge ingestion supports .md, .txt, .pdf, .docx; uses `RecursiveCharacterTextSplitter` (chunk_size=1500, overlap=200)
- After-sales tools use hardcoded mock data dictionaries, not real systems
