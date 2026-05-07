# ITS Multi-Agent System P0 Upgrade Design

## Overview

Upgrade the ITS Multi-Agent Intelligent Customer Service System with three P0 priorities:
1. Langfuse observability and evaluation platform integration
2. Multi-turn conversation context fix
3. RAG retrieval pipeline optimization (HyDE + BM25/Vector hybrid + bge-reranker)

**Implementation order**: Langfuse first (establish measurement baseline) → Multi-turn fix → RAG optimization (quantify improvements via Langfuse).

## Tech Stack

- **Backend**: FastAPI + openai-agents SDK + LangChain + ChromaDB + MySQL
- **Frontend**: Vue 3 + Element Plus
- **LLM**: MiMo-V2.5-Pro (main) / MiniMax-m2.7 (sub) via OpenAI-compatible API
- **New dependencies**: `langfuse`, `rank_bm25`, `FlagEmbedding`
- **Infrastructure**: Docker Compose (Langfuse + PostgreSQL)

---

## Phase 1: Langfuse Integration

### 1.1 Langfuse Local Deployment

Docker Compose file at `docker/langfuse/docker-compose.yml`:

- **langfuse-db**: PostgreSQL 15 Alpine with health check
- **langfuse-server**: `langfuse/langfuse:latest` on port 3001
- Persistent volume for database data
- Environment: `DATABASE_URL`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `SALT`

### 1.2 Langfuse Client

New file: `backend/app/infrastructure/observability/langfuse_client.py`

- Initialize `Langfuse` client with public_key, secret_key, host from settings
- Export `langfuse` singleton instance
- Provide `flush()` method for graceful shutdown

### 1.3 Tracing Strategy

| Layer | Decorator | Data Captured |
|-------|-----------|---------------|
| Agent calls | `@observe(as_type="agent")` | orchestrator/technical/service agent input/output, token usage |
| Tool calls | `@observe(as_type="tool")` | function_tool params, return value, latency |
| RAG retrieval | `@observe(as_type="retrieval")` | query, retrieved docs, top-k scores |
| LLM calls | `@observe(as_type="generation")` | model, prompt, completion, token usage, latency |

### 1.4 Files to Modify

- `backend/app/config/settings.py`: Add `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `backend/app/services/agent_service.py`: Add `@observe()` on `process_task`
- `backend/app/multi_agent/agent_factory.py`: Add `@observe()` on tool functions
- `backend/knowledge/services/retrieval_service.py`: Add `@observe()` on `retrieval`
- `backend/app/api/main.py`: Add `langfuse.flush()` in lifespan shutdown
- `backend/app/requirements.txt`: Add `langfuse>=2.0.0`

---

## Phase 2: Multi-turn Conversation Fix

### 2.1 Problem

In `agent_service.py` lines 41-46, `chat_history` is prepared by `session_service.prepare_history()` but never passed to `Runner.run_streamed()`. The agent only receives `user_query` as input, losing all conversation context.

### 2.2 Fix

```python
# Before (broken):
streaming_result = Runner.run_streamed(
    starting_agent=orchestrator_agent,
    input=user_query,
    ...
)

# After (fixed):
streaming_result = Runner.run_streamed(
    starting_agent=orchestrator_agent,
    input=chat_history,  # Pass full message list
    ...
)
```

The `input` parameter of `Runner.run_streamed()` accepts `list[dict]` with `{"role": ..., "content": ...}` format, which matches `session_service.prepare_history()` output.

### 2.3 Prompt Adjustment

Update `backend/app/prompts/orchestrator_v1.md` to add context utilization rules:

- Pronoun resolution: infer references from history ("it", "that", "last time")
- Continuation handling: "continue", "what else"延续上一轮话题
- Still only process explicit requests in current message, don't replay history

### 2.4 Files to Modify

- `backend/app/services/agent_service.py`: Change `input=user_query` to `input=chat_history`
- `backend/app/prompts/orchestrator_v1.md`: Add context utilization section

---

## Phase 3: RAG Retrieval Optimization

### 3.1 Pipeline Comparison

```
Current:
  query → [vector search] + [jieba title search] → dedup → cosine rerank → top-2

Optimized:
  query → [HyDE rewrite] → [BM25 search] + [vector search] + [jieba title search]
        → dedup → [bge-reranker rerank] → top-K (configurable)
```

### 3.2 HyDE (Hypothetical Document Embedding)

New file: `backend/knowledge/services/hyde.py`

- Class `HyDEService` with method `generate_hypothetical_document(query: str) -> str`
- Calls LLM to generate a 200-word hypothetical technical document that might answer the query
- The hypothetical document's embedding is closer to real documents in vector space than the raw query
- Configurable via `HYDE_ENABLED` setting (default True)

### 3.3 BM25 Retrieval

New file: `backend/knowledge/services/bm25_retriever.py`

- Class `BM25Retriever` using `rank_bm25.BM25Okapi`
- Builds index at startup from all documents in `data/crawl/`
- Uses jieba tokenization for Chinese text
- Method `search(query: str, top_k: int) -> List[Document]`

### 3.4 bge-reranker

New file: `backend/knowledge/services/reranker.py`

- Class `RerankerService` using `FlagEmbedding.FlagReranker`
- Model: `BAAI/bge-reranker-v2-m3` (local, ~1GB, multilingual)
- Method `rerank(query: str, documents: List[str]) -> List[tuple[int, float]]`
- Replaces current cosine similarity reranking

### 3.5 Hybrid Retrieval Fusion

Modified `retrieval_service.py` `retrieval()` method:

1. Generate HyDE hypothetical document
2. Three-way retrieval: BM25 (keyword) + Vector (semantic via HyDE) + Title (jieba)
3. Merge and deduplicate
4. bge-reranker reranking
5. Return top-K documents

### 3.6 New Dependencies

```
rank_bm25>=0.2.2
FlagEmbedding>=1.2.0
```

### 3.7 New Settings

```python
TOP_K_BM25: int = 10
TOP_K_VECTOR: int = 10
TOP_K_TITLE: int = 5
TOP_FINAL: int = 5
HYDE_ENABLED: bool = True
RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
```

### 3.8 Files to Modify

- `backend/knowledge/services/retrieval_service.py`: Rewrite `retrieval()` method
- `backend/knowledge/config/settings.py`: Add new config items
- `backend/knowledge/requirements.txt`: Add `rank_bm25`, `FlagEmbedding`

### 3.9 New Files

- `backend/knowledge/services/hyde.py`
- `backend/knowledge/services/bm25_retriever.py`
- `backend/knowledge/services/reranker.py`

---

## Phase 4: Evaluation Framework

### 4.1 Test Case Structure

New file: `backend/app/evaluation/test_cases.yaml`

Three categories:
- **Intent recognition**: Verify correct agent routing (technical vs service)
- **RAG retrieval**: Verify expected documents are retrieved
- **Multi-turn**: Verify context understanding across turns

### 4.2 LLM-as-Judge

New file: `backend/app/evaluation/judge.py`

5 scoring dimensions (0-10 each):
1. Intent recognition accuracy
2. Answer relevance
3. Answer completeness
4. RAG retrieval quality
5. Multi-turn coherence

Uses LLM to automatically score agent outputs. Writes scores to Langfuse.

### 4.3 Evaluation Runner

New file: `backend/app/evaluation/runner.py`

Execution flow:
1. Load test cases from YAML
2. Execute agent for each case
3. Collect Langfuse trace_id
4. Run LLM-as-Judge evaluation
5. Write scores to Langfuse via `langfuse.score()`

### 4.4 Target Metrics

| Metric | Calculation | Target |
|--------|-------------|--------|
| Intent accuracy | Correct tool calls / Total cases | ≥ 90% |
| RAG recall | Expected doc retrieved / Total cases | ≥ 80% |
| Answer quality avg | LLM-as-Judge mean score | ≥ 7.5/10 |
| Latency P95 | 95th percentile latency | ≤ 10s |
| Token usage avg | Mean tokens per conversation | Baseline reference |

### 4.5 New Files

- `backend/app/evaluation/__init__.py`
- `backend/app/evaluation/test_cases.yaml`
- `backend/app/evaluation/judge.py`
- `backend/app/evaluation/runner.py`
- `backend/app/evaluation/config.py`

---

## File Change Summary

### New Files (8)
| File | Purpose |
|------|---------|
| `docker/langfuse/docker-compose.yml` | Langfuse + PostgreSQL deployment |
| `backend/app/infrastructure/observability/langfuse_client.py` | Langfuse client singleton |
| `backend/knowledge/services/hyde.py` | HyDE query rewriting |
| `backend/knowledge/services/bm25_retriever.py` | BM25 keyword retrieval |
| `backend/knowledge/services/reranker.py` | bge-reranker reranking |
| `backend/app/evaluation/test_cases.yaml` | Test case definitions |
| `backend/app/evaluation/judge.py` | LLM-as-Judge scoring |
| `backend/app/evaluation/runner.py` | Evaluation runner |

### Modified Files (7)
| File | Change |
|------|--------|
| `backend/app/config/settings.py` | Add Langfuse config items |
| `backend/app/services/agent_service.py` | Fix multi-turn input + add @observe |
| `backend/app/multi_agent/agent_factory.py` | Add @observe on tools |
| `backend/app/prompts/orchestrator_v1.md` | Add context utilization rules |
| `backend/knowledge/services/retrieval_service.py` | Rewrite retrieval pipeline |
| `backend/knowledge/config/settings.py` | Add RAG config items |
| `backend/app/api/main.py` | Add langfuse.flush() on shutdown |

### Dependency Changes (2)
| File | Additions |
|------|-----------|
| `backend/app/requirements.txt` | `langfuse>=2.0.0` |
| `backend/knowledge/requirements.txt` | `rank_bm25>=0.2.2`, `FlagEmbedding>=1.2.0` |
