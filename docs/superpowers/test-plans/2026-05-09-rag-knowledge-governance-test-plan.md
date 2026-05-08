# RAG Knowledge Governance Test Plan

## Related Implementation Plan

`docs/superpowers/plans/2026-05-09-rag-knowledge-governance.md`

## Test Objective

Verify that the knowledge service supports enterprise-grade document governance: document registry, status lifecycle, duplicate detection, chunk/vector metadata, citations, delete/reindex operations, and persisted RAG evaluation results.

## Test Scope

In scope:

- `knowledge_documents` and `knowledge_document_chunks`
- Upload lifecycle statuses
- SHA-256 duplicate detection
- Deterministic chunk IDs and vector IDs
- Query response citations
- Document list/delete/reindex APIs
- Knowledge UI display of documents and citations
- RAG evaluation persistence

Out of scope:

- Reranker model quality benchmarking beyond smoke checks
- Real production document permissions
- Full admin RBAC

## Test Environment

Required:

- Knowledge service test database
- Chroma test persist directory
- Mocked embeddings for automated tests
- Optional real embedding model for integration smoke test

Recommended default:

```powershell
cd backend\knowledge
pytest tests\test_document_service.py tests\test_query_citations.py -v
```

Integration:

```powershell
pytest tests -m integration -v
```

## Test Data

Documents:

`kb_blue_screen.md`

```markdown
# Windows 蓝屏处理

如果电脑开机蓝屏，先记录错误代码。常见代码 0x0000007B 与硬盘控制器或启动配置有关。
```

`kb_network.md`

```markdown
# 网络连接异常

如果网页打不开但 QQ 可以登录，检查 DNS 设置、代理设置和浏览器配置。
```

Duplicate:

- Same content as `kb_blue_screen.md` but filename `copy_blue_screen.md`

Expected citations:

- `title`: `Windows 蓝屏处理`
- `source_filename`: `kb_blue_screen.md`
- `chunk_index`: `0`

## Automated Test Cases

### RAG-DOC-001: Document Tables Initialize Idempotently

Type: repository integration test

Steps:

1. Call document/chunk/evaluation table initialization.
2. Call them again.
3. Query `information_schema.tables`.

Expected:

- No exception.
- Tables exist:
  - `knowledge_documents`
  - `knowledge_document_chunks`
  - `rag_evaluation_runs`
  - `rag_evaluation_cases`

### RAG-UP-001: Upload Creates Document Registry Row

Type: API test with mocked vector store

Steps:

1. Upload `kb_blue_screen.md`.
2. Query `knowledge_documents`.

Expected:

- One row created.
- `status` eventually equals `indexed`.
- `chunk_count > 0`.
- `file_hash` is 64-character SHA-256.
- `original_filename` equals `kb_blue_screen.md`.

### RAG-UP-002: Upload Lifecycle Status Order

Type: service test

Steps:

1. Instrument or mock `DocumentRepository.update_status()`.
2. Upload valid markdown.

Expected status calls in order:

```text
uploaded -> parsing -> embedding -> indexed
```

If parsing fails:

```text
uploaded -> parsing -> failed
```

### RAG-UP-003: Duplicate Upload Is Skipped

Type: API test

Steps:

1. Upload `kb_blue_screen.md`.
2. Upload `copy_blue_screen.md` with identical content.

Expected:

- Second response has `duplicate: true`.
- `chunks_added: 0`.
- No new active document row with same hash.
- No new vectors are added.

### RAG-UP-004: Failed Parse Records Failed Status

Type: service test

Setup:

- Mock parser to raise `ValueError("parse failed")`.

Steps:

1. Upload a document.

Expected:

- API returns error.
- Document row has `status="failed"`.
- `error_message` contains `parse failed`.
- No chunk rows are created.

### RAG-CHUNK-001: Chunk IDs Are Deterministic

Type: ingestion unit test

Steps:

1. Upload document with `document_id="doc123"`.
2. Inspect chunk metadata.

Expected:

```text
doc123:chunk:0
doc123:chunk:1
```

Each chunk metadata includes:

- `document_id`
- `chunk_id`
- `chunk_index`
- `title`
- `source_filename`

### RAG-VEC-001: Vector Store Receives Explicit IDs

Type: repository test with mocked Chroma

Steps:

1. Call `VectorStoreRepository.add_documents(docs, ids=["doc123:chunk:0"])`.
2. Assert Chroma `add_documents` was called with matching `ids`.

Expected:

- Vector IDs equal chunk IDs.
- Batch insertion preserves ID order.

### RAG-QRY-001: Query Response Includes Citations

Type: API test with mocked retrieval

Setup:

Mock `retrieval_service.retrieval()` to return one `Document` with metadata:

```python
{
  "document_id": "doc123",
  "chunk_id": "doc123:chunk:0",
  "title": "Windows 蓝屏处理",
  "source_filename": "kb_blue_screen.md",
  "chunk_index": 0,
  "reranker_score": 0.91
}
```

Steps:

1. POST `/query` with question `电脑蓝屏怎么办`.

Expected:

- Response includes `answer`.
- Response includes `citations`.
- First citation has `document_id="doc123"`, `chunk_id="doc123:chunk:0"`, `title="Windows 蓝屏处理"`.

### RAG-QRY-002: Duplicate Citations Are Deduplicated

Type: unit test

Steps:

1. Call `build_citations()` with two documents sharing same `chunk_id`.

Expected:

- Only one citation for the same `chunk_id`.

### RAG-DOCAPI-001: List Documents Returns Pagination

Type: API test

Steps:

1. Insert 3 document rows.
2. GET `/documents?limit=2&offset=0`.

Expected:

- `total >= 3`.
- `len(documents) == 2`.
- Each document includes `document_id`, `filename`, `status`, `chunk_count`, `created_at`.

### RAG-DOCAPI-002: Delete Document Removes Vectors And Excludes Retrieval

Type: API/integration test with mocked vector store

Steps:

1. Upload document.
2. DELETE `/documents/{document_id}`.
3. Query document row.
4. Query retrieval for related question.

Expected:

- Vector delete called with chunk IDs.
- Document status becomes `deleted`.
- Deleted document is not returned in retrieval candidates.

### RAG-DOCAPI-003: Reindex Rebuilds Chunks

Type: API test

Steps:

1. Upload document.
2. Modify stored file content.
3. POST `/documents/{document_id}/reindex`.
4. Query chunks.

Expected:

- Old chunks are removed or replaced.
- New chunks use same `document_id` and new chunk IDs.
- Document status returns to `indexed`.
- `chunk_count` matches new chunk count.

### RAG-EVAL-001: Evaluation Run Is Persisted

Type: evaluator test

Setup:

- Mock knowledge query and RAGAS result.

Steps:

1. Run `run_rag_evaluation()`.
2. Query `rag_evaluation_runs`.
3. Query `rag_evaluation_cases`.

Expected:

- One run row exists.
- Run has summary metrics JSON.
- Case rows exist for each test case.
- `latency_ms` is recorded.

### RAG-FE-001: Knowledge UI Displays Document Registry

Type: manual UI test

Steps:

1. Start knowledge UI.
2. Upload document.
3. View document table.

Expected:

- Table displays filename, status, chunk count, upload time.
- Delete and reindex buttons are visible for indexed documents.

### RAG-FE-002: Knowledge UI Displays Citations

Type: manual UI test

Steps:

1. Ask `电脑蓝屏怎么办`.
2. Inspect assistant answer.

Expected:

- Answer renders normally.
- `参考来源` section appears.
- Source title or filename is visible.

## Regression Tests

Run:

```powershell
cd backend\knowledge
pytest tests -m "not integration" -v
cd ..\..\front\knowlege_platform_ui
npm run build
```

Expected:

- Tests pass.
- Knowledge UI build succeeds.

## Quality Checks

### RAG-QUAL-001: Retrieval Still Returns Relevant Blue Screen Document

Type: integration test

Steps:

1. Ingest `kb_blue_screen.md`.
2. Query `电脑开机蓝屏 0x0000007B`.

Expected:

- Retrieved contexts include `0x0000007B`.
- Citation references `kb_blue_screen.md`.

## Acceptance Gate

The feature passes when:

- Document lifecycle is persisted.
- Duplicate files are skipped.
- Citations are returned and displayed.
- Delete/reindex work without orphaned active vectors.
- Evaluation runs are persisted.
- Existing `/query` consumers still work with the extended response.

