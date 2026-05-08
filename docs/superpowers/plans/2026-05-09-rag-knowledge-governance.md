# RAG Knowledge Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing RAG service into a governed knowledge platform with document records, ingestion lifecycle, deduplication, citations, delete/reindex operations, and persisted evaluation results.

**Architecture:** Keep the current HyDE + BM25 + vector + title + reranker retrieval pipeline. Add a MySQL document registry around ingestion and retrieval, store chunk metadata and vector IDs, return citation metadata from query endpoints, and expose document management APIs for the knowledge UI.

**Tech Stack:** FastAPI, MySQL, ChromaDB, LangChain documents, DashScope embeddings, RAGAS, Vue 3 knowledge UI.

---

## File Map

Create:

- `backend/knowledge/repositories/document_repository.py`
- `backend/knowledge/repositories/chunk_repository.py`
- `backend/knowledge/repositories/evaluation_repository.py`
- `backend/knowledge/services/document_service.py`
- `backend/knowledge/services/citation_service.py`
- `backend/knowledge/tests/test_document_service.py`
- `backend/knowledge/tests/test_query_citations.py`

Modify:

- `backend/knowledge/config/settings.py`
- `backend/knowledge/schemas/schema.py`
- `backend/knowledge/api/routers.py`
- `backend/knowledge/services/ingestion/ingestion_processor.py`
- `backend/knowledge/repositories/vector_store_repository.py`
- `backend/knowledge/services/retrieval_service.py`
- `backend/knowledge/services/query_service.py`
- `backend/app/evaluation/rag_evaluator.py`
- `front/knowlege_platform_ui/src/api/knowledge.js`
- `front/knowlege_platform_ui/src/views/Knowledge.vue`
- `front/knowlege_platform_ui/src/views/Chat.vue`

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_hash CHAR(64) NOT NULL,
    file_ext VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT NULL,
    chunk_count INT NOT NULL DEFAULT 0,
    uploaded_by VARCHAR(128) NULL,
    storage_path VARCHAR(512) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uq_document_id (document_id),
    UNIQUE KEY uq_file_hash_active (file_hash, deleted_at),
    INDEX idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS knowledge_document_chunks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    document_pk BIGINT NOT NULL,
    chunk_id VARCHAR(128) NOT NULL,
    chunk_index INT NOT NULL,
    title VARCHAR(255) NULL,
    content_preview TEXT NULL,
    vector_id VARCHAR(128) NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_chunk_id (chunk_id),
    INDEX idx_document_chunk (document_pk, chunk_index),
    CONSTRAINT fk_chunks_document FOREIGN KEY (document_pk) REFERENCES knowledge_documents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rag_evaluation_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    metrics JSON NULL,
    case_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    UNIQUE KEY uq_eval_run_id (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rag_evaluation_cases (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_pk BIGINT NOT NULL,
    case_id VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    answer MEDIUMTEXT NULL,
    contexts JSON NULL,
    metrics JSON NULL,
    latency_ms INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_eval_cases_run FOREIGN KEY (run_pk) REFERENCES rag_evaluation_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## Status Lifecycle

Documents must move through these statuses:

```text
uploaded -> parsing -> embedding -> indexed
uploaded -> parsing -> failed
indexed -> deleting -> deleted
indexed -> reindexing -> indexed
```

No query result should cite `deleted` or `failed` documents.

## Task 1: Document Registry

**Files:**

- Create: `backend/knowledge/repositories/document_repository.py`
- Create: `backend/knowledge/repositories/chunk_repository.py`
- Create: `backend/knowledge/services/document_service.py`
- Modify: `backend/knowledge/api/main.py` or startup path if initialization is centralized

- [ ] **Step 1: Add repositories**

`DocumentRepository` should provide these methods:

| Method | Required behavior |
| --- | --- |
| `init_tables() -> None` | Create document and chunk tables when missing. |
| `create_document(document_id: str, filename: str, original_filename: str, file_hash: str, file_ext: str, storage_path: str | None) -> dict` | Insert an `uploaded` document row and return the inserted record. |
| `get_by_hash(file_hash: str) -> dict | None` | Return the latest non-deleted document with that hash. |
| `get_by_document_id(document_id: str) -> dict | None` | Return one document record by stable ID. |
| `update_status(document_id: str, status: str, error_message: str | None = None, chunk_count: int | None = None) -> None` | Update lifecycle state and optional error/chunk count. |
| `list_documents(status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]` | Return paginated documents, optionally filtered by status. |
| `mark_deleted(document_id: str) -> bool` | Set status/deleted timestamp and return whether a row changed. |

`ChunkRepository` should provide these methods:

| Method | Required behavior |
| --- | --- |
| `insert_chunks(document_pk: int, chunks: list[dict]) -> None` | Bulk insert chunk metadata for a document. |
| `delete_chunks_by_document(document_pk: int) -> None` | Remove chunk metadata when rebuilding an index. |
| `get_chunks_by_document(document_pk: int) -> list[dict]` | Return chunks in `chunk_index` order. |

- [ ] **Step 2: Add table initialization**

Initialize both tables when the knowledge service starts.

- [ ] **Step 3: Commit**

```powershell
git add backend/knowledge/repositories/document_repository.py backend/knowledge/repositories/chunk_repository.py backend/knowledge/services/document_service.py backend/knowledge/api/main.py
git commit -m "feat: add knowledge document registry tables"
```

## Task 2: Hash-Based Deduplication And Ingestion Status

**Files:**

- Modify: `backend/knowledge/api/routers.py`
- Modify: `backend/knowledge/services/ingestion/ingestion_processor.py`
- Modify: `backend/knowledge/schemas/schema.py`
- Test: `backend/knowledge/tests/test_document_service.py`

- [ ] **Step 1: Extend upload response**

Add:

```python
class UploadResponse(BaseModel):
    status: str
    message: str
    file_name: str
    chunks_added: int
    document_id: str | None = None
    duplicate: bool = False
```

- [ ] **Step 2: Compute file hash**

After writing the uploaded file to a safe temporary path, compute SHA-256:

```python
def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 3: Reject active duplicates**

If `DocumentRepository.get_by_hash(file_hash)` returns an active `indexed`, `parsing`, or `embedding` document, return:

```json
{
  "status": "success",
  "message": "文档已存在，跳过重复入库",
  "file_name": "xxx.md",
  "chunks_added": 0,
  "document_id": "existing-id",
  "duplicate": true
}
```

- [ ] **Step 4: Record lifecycle**

Upload flow:

1. Create document row with `status="uploaded"`.
2. Set `status="parsing"`.
3. Parse and split.
4. Set `status="embedding"`.
5. Add vectors and chunks.
6. Set `status="indexed"` with `chunk_count`.
7. On exception, set `status="failed"` with error message.

- [ ] **Step 5: Tests**

Test:

- First upload creates document.
- Same content second upload returns duplicate.
- Parsing error sets failed status.

- [ ] **Step 6: Commit**

```powershell
git add backend/knowledge/api/routers.py backend/knowledge/services/ingestion/ingestion_processor.py backend/knowledge/schemas/schema.py backend/knowledge/tests/test_document_service.py
git commit -m "feat: track knowledge ingestion status and deduplicate uploads"
```

## Task 3: Chunk IDs And Vector Metadata

**Files:**

- Modify: `backend/knowledge/repositories/vector_store_repository.py`
- Modify: `backend/knowledge/services/ingestion/ingestion_processor.py`
- Modify: `backend/knowledge/repositories/chunk_repository.py`

- [ ] **Step 1: Generate deterministic chunk IDs**

Chunk ID format:

```text
{document_id}:chunk:{chunk_index}
```

Each LangChain `Document.metadata` should include:

```python
{
    "document_id": document_id,
    "chunk_id": chunk_id,
    "chunk_index": chunk_index,
    "title": title,
    "source_filename": original_filename
}
```

- [ ] **Step 2: Add Chroma documents with IDs**

Update `VectorStoreRepository.add_documents()` to accept optional `ids`:

```python
def add_documents(self, documents: list[Document], ids: list[str] | None = None, batch_size: int = 10) -> int:
    self.vector_database.add_documents(batch, ids=batch_ids)
```

- [ ] **Step 3: Store chunks in MySQL**

After vector insert, insert chunk records:

```python
{
  "chunk_id": chunk_id,
  "chunk_index": index,
  "title": title,
  "content_preview": doc.page_content[:500],
  "vector_id": chunk_id,
  "metadata": doc.metadata
}
```

- [ ] **Step 4: Commit**

```powershell
git add backend/knowledge/repositories/vector_store_repository.py backend/knowledge/services/ingestion/ingestion_processor.py backend/knowledge/repositories/chunk_repository.py
git commit -m "feat: persist chunk metadata and deterministic vector IDs"
```

## Task 4: Citations In Query Responses

**Files:**

- Create: `backend/knowledge/services/citation_service.py`
- Modify: `backend/knowledge/schemas/schema.py`
- Modify: `backend/knowledge/api/routers.py`
- Modify: `backend/knowledge/services/query_service.py`
- Test: `backend/knowledge/tests/test_query_citations.py`

- [ ] **Step 1: Add citation schema**

```python
class Citation(BaseModel):
    document_id: str | None = None
    chunk_id: str | None = None
    title: str | None = None
    source_filename: str | None = None
    chunk_index: int | None = None
    score: float | None = None

class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = []
```

- [ ] **Step 2: Build citations from retrieved documents**

`citation_service.py`:

```python
def build_citations(documents: list[Document]) -> list[dict]:
    citations = []
    seen = set()
    for doc in documents:
        metadata = doc.metadata or {}
        key = metadata.get("chunk_id") or (metadata.get("title"), metadata.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "document_id": metadata.get("document_id"),
            "chunk_id": metadata.get("chunk_id"),
            "title": metadata.get("title"),
            "source_filename": metadata.get("source_filename") or metadata.get("path"),
            "chunk_index": metadata.get("chunk_index"),
            "score": metadata.get("reranker_score") or metadata.get("similarity") or metadata.get("bm25_score"),
        })
    return citations
```

- [ ] **Step 3: Return citations**

In `/query`, return `QueryResponse(question=user_question, answer=answer, citations=citations)`.

- [ ] **Step 4: Display citations in knowledge UI**

In `front/knowlege_platform_ui/src/views/Chat.vue`, under assistant answer, render a compact list:

```text
参考来源:
1. Windows 7 开机蓝屏提示问题的解决方案
2. 台式和一体机蓝屏报错代码：0x0000007B
```

- [ ] **Step 5: Tests**

Test that `/query` returns `citations` and each citation has at least `title` or `source_filename`.

- [ ] **Step 6: Commit**

```powershell
git add backend/knowledge/services/citation_service.py backend/knowledge/schemas/schema.py backend/knowledge/api/routers.py backend/knowledge/services/query_service.py backend/knowledge/tests/test_query_citations.py front/knowlege_platform_ui/src/views/Chat.vue
git commit -m "feat: return and display RAG source citations"
```

## Task 5: Document List, Delete, And Reindex APIs

**Files:**

- Modify: `backend/knowledge/api/routers.py`
- Modify: `backend/knowledge/repositories/vector_store_repository.py`
- Modify: `front/knowlege_platform_ui/src/api/knowledge.js`
- Modify: `front/knowlege_platform_ui/src/views/Knowledge.vue`

- [ ] **Step 1: Add API schemas**

```python
class DocumentListResponse(BaseModel):
    total: int
    documents: list[dict]

class DocumentActionResponse(BaseModel):
    success: bool
    document_id: str
    message: str
```

- [ ] **Step 2: Add endpoints**

Add these endpoints:

| Endpoint | Behavior |
| --- | --- |
| `GET /documents?status=&limit=&offset=` | Return `DocumentListResponse` with paginated document records. |
| `DELETE /documents/{document_id}` | Delete vectors for the document, mark document deleted, and return `DocumentActionResponse`. |
| `POST /documents/{document_id}/reindex` | Re-parse the stored file, rebuild chunks/vectors, update status, and return `DocumentActionResponse`. |

- [ ] **Step 3: Delete vectors by IDs**

Add:

```python
def delete_by_ids(self, ids: list[str]) -> None:
    self.vector_database.delete(ids=ids)
```

Delete operation:

1. Load document.
2. Load chunk vector IDs.
3. Delete vectors.
4. Mark document deleted.
5. Delete or retain chunk rows with document status as deleted. Prefer retaining rows for audit and excluding deleted documents from retrieval.

- [ ] **Step 4: Update UI**

Knowledge page should show:

- filename
- status
- chunks
- upload time
- actions: delete, reindex

- [ ] **Step 5: Commit**

```powershell
git add backend/knowledge/api/routers.py backend/knowledge/repositories/vector_store_repository.py front/knowlege_platform_ui/src/api/knowledge.js front/knowlege_platform_ui/src/views/Knowledge.vue
git commit -m "feat: add knowledge document management APIs and UI"
```

## Task 6: Persist RAG Evaluation Results

**Files:**

- Create: `backend/knowledge/repositories/evaluation_repository.py`
- Modify: `backend/app/evaluation/rag_evaluator.py`
- Optional Modify: `backend/knowledge/api/routers.py`

- [ ] **Step 1: Add evaluation repository**

Provide these methods:

| Method | Required behavior |
| --- | --- |
| `create_run(run_id: str, status: str, case_count: int) -> int` | Insert an evaluation run and return its primary key. |
| `complete_run(run_id: str, metrics: dict) -> None` | Store summary metrics and set `completed_at`. |
| `insert_case(run_pk: int, case_id: str, question: str, answer: str, contexts: list[str], metrics: dict, latency_ms: int) -> None` | Persist one evaluated case. |
| `list_runs(limit: int = 20) -> list[dict]` | Return recent evaluation runs for UI/API display. |

- [ ] **Step 2: Persist evaluator output**

`rag_evaluator.py` should write:

- one run row
- one row per case
- summary metrics JSON

- [ ] **Step 3: Optional endpoint**

Add:

Add `GET /evaluation/runs`, returning recent evaluation runs from `EvaluationRepository.list_runs()`.

- [ ] **Step 4: Commit**

```powershell
git add backend/knowledge/repositories/evaluation_repository.py backend/app/evaluation/rag_evaluator.py backend/knowledge/api/routers.py
git commit -m "feat: persist RAG evaluation results"
```

## Acceptance Criteria

- Uploading a new document creates a `knowledge_documents` row.
- Duplicate uploads are detected by hash.
- Ingestion status is visible and accurate.
- Query responses include `citations`.
- Knowledge UI shows documents and citations.
- Delete removes vectors or excludes the document from future retrieval.
- Reindex rebuilds chunks/vectors for a document.
- RAG evaluation results are persisted.
- Existing retrieval quality pipeline remains intact.

## Resume Bullet

> Upgraded the RAG subsystem into a governed knowledge platform with document lifecycle management, hash deduplication, deterministic chunk/vector metadata, source citations, delete/reindex operations, and persisted RAG evaluation metrics.
