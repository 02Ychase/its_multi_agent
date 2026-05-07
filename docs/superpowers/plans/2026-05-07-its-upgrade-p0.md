# ITS Multi-Agent P0 Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Langfuse observability, fix multi-turn conversation, and optimize RAG retrieval pipeline (HyDE + BM25 + bge-reranker) for the ITS Multi-Agent system.

**Architecture:** Langfuse tracing layer wraps all agent/tool/RAG calls via `@observe()` decorators. Multi-turn fix passes chat history to `Runner.run_streamed()`. RAG pipeline upgrades from 2-way cosine rerank to 3-way hybrid retrieval with bge-reranker.

**Tech Stack:** FastAPI, openai-agents SDK, LangChain, ChromaDB, Langfuse, rank_bm25, FlagEmbedding (bge-reranker-v2-m3)

---

## Phase 1: Langfuse Integration

### Task 1: Create Langfuse Docker Compose

**Files:**
- Create: `docker/langfuse/docker-compose.yml`

- [ ] **Step 1: Create docker directory and compose file**

```bash
mkdir -p docker/langfuse
```

Create `docker/langfuse/docker-compose.yml`:

```yaml
services:
  langfuse-db:
    image: postgres:15-alpine
    container_name: langfuse-db
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse_secret
      POSTGRES_DB: langfuse
    volumes:
      - langfuse-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  langfuse-server:
    image: langfuse/langfuse:latest
    container_name: langfuse-server
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse_secret@langfuse-db:5432/langfuse
      NEXTAUTH_SECRET: its-multi-agent-secret-key-change-in-production
      NEXTAUTH_URL: http://localhost:3001
      SALT: its-multi-agent-salt-change-in-production
    depends_on:
      langfuse-db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  langfuse-db-data:
```

- [ ] **Step 2: Start Langfuse and verify**

```bash
cd docker/langfuse && docker compose up -d
```

Open http://localhost:3001 in browser. Create a new project named "its-multi-agent". Go to Project Settings → API Keys and note the `Public Key` and `Secret Key`.

- [ ] **Step 3: Commit**

```bash
git add docker/langfuse/docker-compose.yml
git commit -m "infra: add Langfuse Docker Compose for local deployment"
```

---

### Task 2: Add Langfuse Configuration

**Files:**
- Modify: `backend/app/config/settings.py:64-68`
- Modify: `backend/app/.env` (add Langfuse keys)

- [ ] **Step 1: Add Langfuse settings to Settings class**

In `backend/app/config/settings.py`, add after line 68 (after `BAIDUMAP_AK`):

```python
    # ==================== Langfuse 可观测性配置 ====================

    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse Public Key"
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse Secret Key"
    )
    LANGFUSE_HOST: Optional[str] = Field(
        default="http://localhost:3001",
        description="Langfuse Server URL"
    )
```

- [ ] **Step 2: Add Langfuse keys to .env**

Append to `backend/app/.env`:

```
# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-xxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxx
LANGFUSE_HOST=http://localhost:3001
```

Replace `pk-lf-xxxx` and `sk-lf-xxxx` with actual keys from Task 1 Step 2.

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/settings.py backend/app/.env
git commit -m "config: add Langfuse settings to application config"
```

---

### Task 3: Add langfuse Dependency

**Files:**
- Modify: `backend/app/requirements.txt`

- [ ] **Step 1: Add langfuse to requirements.txt**

Append to `backend/app/requirements.txt`:

```
langfuse>=2.0.0
```

- [ ] **Step 2: Install dependency**

```bash
cd backend/app && pip install langfuse>=2.0.0
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/requirements.txt
git commit -m "deps: add langfuse dependency"
```

---

### Task 4: Create Langfuse Client

**Files:**
- Create: `backend/app/infrastructure/observability/__init__.py`
- Create: `backend/app/infrastructure/observability/langfuse_client.py`

- [ ] **Step 1: Create observability package init**

Create `backend/app/infrastructure/observability/__init__.py`:

```python
```

- [ ] **Step 2: Create Langfuse client module**

Create `backend/app/infrastructure/observability/langfuse_client.py`:

```python
from langfuse import Langfuse
from config.settings import settings


def create_langfuse_client() -> Langfuse:
    """Create Langfuse client from settings. Returns disabled client if keys not configured."""
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return Langfuse(enabled=False)

    return Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )


langfuse = create_langfuse_client()


def flush_langfuse():
    """Flush pending Langfuse events. Call on application shutdown."""
    try:
        langfuse.flush()
    except Exception:
        pass
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/infrastructure/observability/
git commit -m "feat: add Langfuse client singleton"
```

---

### Task 5: Add @observe to agent_service.py

**Files:**
- Modify: `backend/app/services/agent_service.py:1-10,21-22`

- [ ] **Step 1: Add imports and @observe decorator**

Replace the imports and class definition in `backend/app/services/agent_service.py`:

```python
import re
from collections.abc import AsyncGenerator
from agents.run import Runner, RunConfig
from langfuse.decorators import observe
from multi_agent.orchestrator_agent import orchestrator_agent
from schemas.request import ChatMessageRequest
from services.session_service import session_service
from services.stream_response_service import process_stream_response
from utils.response_util import ResponseFactory
from infrastructure.logging.logger import logger
import traceback
from schemas.response import ContentKind


class MultiAgentService:
    """
    多智能体业务服务类
    """

    @classmethod
    @observe(as_type="agent", name="orchestrator")
    async def process_task(cls, request: ChatMessageRequest, flag: bool) -> AsyncGenerator:
```

Keep the rest of the method body unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/agent_service.py
git commit -m "feat: add Langfuse @observe tracing to agent service"
```

---

### Task 6: Add @observe to agent_factory.py tools

**Files:**
- Modify: `backend/app/multi_agent/agent_factory.py:1-6,12-13,41-42`

- [ ] **Step 1: Add imports and @observe decorators**

Replace the imports and tool function signatures in `backend/app/multi_agent/agent_factory.py`:

```python
from agents import function_tool, Runner
from agents.run import RunConfig
from langfuse.decorators import observe

from multi_agent.technical_agent import technical_agent
from multi_agent.service_agent import comprehensive_service_agent
from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client

from infrastructure.logging.logger import logger


# 1. 定义技术专家智能体工具
@function_tool
@observe(as_type="tool", name="consult_technical_expert")
async def consult_technical_expert(
        query: str,
) -> str:
```

And for the second tool:

```python
# 2. 定义全能业务智能体工具
@function_tool
@observe(as_type="tool", name="query_service_station_and_navigate")
async def query_service_station_and_navigate(
        query: str,
) -> str:
```

Keep the rest of each function body unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/multi_agent/agent_factory.py
git commit -m "feat: add Langfuse @observe tracing to agent tools"
```

---

### Task 7: Add langfuse.flush() to application lifespan

**Files:**
- Modify: `backend/app/api/main.py:1-7,28-34`

- [ ] **Step 1: Add flush to shutdown**

In `backend/app/api/main.py`, add the import and flush call:

```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routers import router
from infrastructure.logging.logger import logger
from infrastructure.tools.mcp.mcp_manager import mcp_connect, mcp_cleanup
from infrastructure.observability.langfuse_client import flush_langfuse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理
    """
    logger.info("应用启动，建立MCP连接...")
    try:
        await mcp_connect()
        logger.info("MCP连接建立完成")
    except Exception as e:
        logger.error(f"MCP连接建立失败: {str(e)}")

    yield

    logger.info("应用关闭，清理MCP连接...")
    try:
        await mcp_cleanup()
        logger.info("MCP连接清理完成")
    except Exception as e:
        logger.error(f"MCP连接清理失败: {str(e)}")

    flush_langfuse()
    logger.info("Langfuse事件已刷新")
```

Keep the rest of the file unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/main.py
git commit -m "feat: add Langfuse flush on application shutdown"
```

---

## Phase 2: Multi-turn Conversation Fix

### Task 8: Fix multi-turn conversation in agent_service.py

**Files:**
- Modify: `backend/app/services/agent_service.py:40-46`

- [ ] **Step 1: Pass chat_history to Runner.run_streamed**

In `backend/app/services/agent_service.py`, change lines 40-46 from:

```python
            # 3. 运行Agent (流式模式)
            streaming_result = Runner.run_streamed(
                starting_agent=orchestrator_agent,
                input=user_query,  # 直接传递用户输入
                max_turns=5,  # COT(思考 行动 观察)--->迭代多少次（不是异常重试）
                run_config=RunConfig(tracing_disabled=True)
            )
```

To:

```python
            # 3. 运行Agent (流式模式，传入完整历史对话)
            streaming_result = Runner.run_streamed(
                starting_agent=orchestrator_agent,
                input=chat_history,
                max_turns=5,
                run_config=RunConfig(tracing_disabled=True)
            )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/agent_service.py
git commit -m "fix: pass chat_history to Runner for multi-turn conversation support"
```

---

### Task 9: Update orchestrator prompt for context utilization

**Files:**
- Modify: `backend/app/prompts/orchestrator_v1.md`

- [ ] **Step 1: Add context utilization section**

Append the following section to the end of `backend/app/prompts/orchestrator_v1.md`:

```markdown

## 🔗 上下文利用规则

### 代词消解
- 当用户使用代词（"它"、"那个"、"这个"、"上次"、"之前"）时，基于历史对话推断指代对象
- 例如：用户之前问了"电脑蓝屏"，现在说"它还能修吗" → "它"指代电脑

### 话题延续
- 当用户说"继续"、"还有呢"、"然后呢"时，延续上一轮的话题
- 例如：用户之前问了维修站，现在说"还有别的吗" → 继续查找更多维修站

### 关键约束
- 上下文利用仅用于理解用户意图，不要重复执行历史中已完成的任务
- 每次只处理当前消息中的明确请求
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/prompts/orchestrator_v1.md
git commit -m "prompt: add context utilization rules for multi-turn conversation"
```

---

## Phase 3: RAG Retrieval Optimization

### Task 10: Add RAG configuration settings

**Files:**
- Modify: `backend/knowledge/config/settings.py:28-31`

- [ ] **Step 1: Add new RAG settings**

In `backend/knowledge/config/settings.py`, add after line 31 (`TOP_FINAL`):

```python
    # BM25 retrieval configuration
    TOP_K_BM25: int = 10

    # HyDE configuration
    HYDE_ENABLED: bool = True

    # Reranker configuration
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_ENABLED: bool = True
```

- [ ] **Step 2: Commit**

```bash
git add backend/knowledge/config/settings.py
git commit -m "config: add RAG optimization settings (BM25, HyDE, Reranker)"
```

---

### Task 11: Add RAG dependencies

**Files:**
- Modify: `backend/knowledge/requirements.txt`

- [ ] **Step 1: Add new dependencies**

Append to `backend/knowledge/requirements.txt`:

```
rank_bm25>=0.2.2
FlagEmbedding>=1.2.0
langfuse>=2.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend/knowledge && pip install rank_bm25>=0.2.2 FlagEmbedding>=1.2.0
```

Note: FlagEmbedding will download the bge-reranker-v2-m3 model (~1GB) on first use.

- [ ] **Step 3: Commit**

```bash
git add backend/knowledge/requirements.txt
git commit -m "deps: add rank_bm25 and FlagEmbedding for RAG optimization"
```

---

### Task 12: Create HyDE service

**Files:**
- Create: `backend/knowledge/services/hyde.py`

- [ ] **Step 1: Create HyDE service**

Create `backend/knowledge/services/hyde.py`:

```python
from langchain_openai import ChatOpenAI
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HyDEService:
    """
    HyDE (Hypothetical Document Embedding) Service.
    Generates a hypothetical document that might answer the user's query,
    then uses its embedding for vector search instead of the raw query.
    """

    HYDE_PROMPT = """你是一位资深的电脑技术工程师。请针对以下用户问题，撰写一段可能包含答案的技术文档片段（约200字）。
这段文档应该像是从一篇技术手册或FAQ中摘录的，包含具体的操作步骤或解决方案。

用户问题：{query}

请直接输出文档片段内容，不要添加任何前缀或解释："""

    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.BASE_URL,
            temperature=0.7,
        )

    def generate_hypothetical_document(self, query: str) -> str:
        """
        Generate a hypothetical document that might answer the query.

        Args:
            query: The user's question

        Returns:
            A hypothetical document string
        """
        try:
            prompt = self.HYDE_PROMPT.format(query=query)
            response = self.llm.invoke(prompt)
            hypothetical_doc = response.content.strip()
            logger.info(f"HyDE generated document ({len(hypothetical_doc)} chars)")
            return hypothetical_doc
        except Exception as e:
            logger.warning(f"HyDE generation failed, falling back to original query: {e}")
            return query


hyde_service = HyDEService()
```

- [ ] **Step 2: Commit**

```bash
git add backend/knowledge/services/hyde.py
git commit -m "feat: add HyDE (Hypothetical Document Embedding) service"
```

---

### Task 13: Create BM25 retriever

**Files:**
- Create: `backend/knowledge/services/bm25_retriever.py`

- [ ] **Step 1: Create BM25 retriever**

Create `backend/knowledge/services/bm25_retriever.py`:

```python
import os
import logging
import jieba
from typing import List
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25 keyword-based retriever for Chinese documents.
    Builds index at startup from all markdown files in the crawl directory.
    """

    def __init__(self):
        self.corpus_texts: List[str] = []
        self.corpus_paths: List[str] = []
        self.corpus_titles: List[str] = []
        self.bm25: BM25Okapi | None = None
        self._build_index()

    def _build_index(self):
        """Build BM25 index from all markdown files in crawl directory."""
        crawl_dir = settings.CRAWL_OUTPUT_DIR
        if not os.path.exists(crawl_dir):
            logger.warning(f"Crawl directory not found: {crawl_dir}")
            return

        md_files = [f for f in os.listdir(crawl_dir) if f.endswith('.md')]
        if not md_files:
            logger.warning(f"No markdown files found in {crawl_dir}")
            return

        tokenized_corpus = []
        for md_file in md_files:
            file_path = os.path.join(crawl_dir, md_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    continue

                title = os.path.splitext(md_file)[0]
                # Remove numeric prefix like "0004-"
                if '-' in title:
                    title = title.split('-', 1)[1]

                self.corpus_texts.append(content)
                self.corpus_paths.append(file_path)
                self.corpus_titles.append(title)

                # Tokenize with jieba for Chinese text
                tokens = list(jieba.cut(content))
                tokenized_corpus.append(tokens)
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue

        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 index built with {len(tokenized_corpus)} documents")
        else:
            logger.warning("BM25 index is empty - no documents loaded")

    def search(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Search for documents matching the query using BM25.

        Args:
            query: The search query
            top_k: Number of top results to return

        Returns:
            List of Document objects sorted by BM25 score
        """
        if self.bm25 is None or not self.corpus_texts:
            return []

        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k indices sorted by score descending
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        documents = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            doc = Document(
                page_content=self.corpus_texts[idx],
                metadata={
                    "path": self.corpus_paths[idx],
                    "title": self.corpus_titles[idx],
                    "bm25_score": float(scores[idx]),
                }
            )
            documents.append(doc)

        logger.info(f"BM25 retrieved {len(documents)} documents for query: {query[:30]}...")
        return documents


bm25_retriever = BM25Retriever()
```

- [ ] **Step 2: Commit**

```bash
git add backend/knowledge/services/bm25_retriever.py
git commit -m "feat: add BM25 keyword retriever for hybrid search"
```

---

### Task 14: Create bge-reranker service

**Files:**
- Create: `backend/knowledge/services/reranker.py`

- [ ] **Step 1: Create reranker service**

Create `backend/knowledge/services/reranker.py`:

```python
import logging
from typing import List, Tuple
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RerankerService:
    """
    Reranking service using BAAI/bge-reranker-v2-m3.
    Replaces cosine similarity reranking with a cross-encoder model.
    """

    def __init__(self):
        self.reranker = None
        self._load_model()

    def _load_model(self):
        """Lazy load the reranker model."""
        try:
            from FlagEmbedding import FlagReranker
            self.reranker = FlagReranker(
                settings.RERANKER_MODEL,
                use_fp16=True
            )
            logger.info(f"Reranker model loaded: {settings.RERANKER_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.reranker = None

    def rerank(self, query: str, documents: list, top_k: int = None) -> list:
        """
        Rerank documents based on relevance to query.

        Args:
            query: The user's question
            documents: List of Document objects to rerank
            top_k: Number of top results to return (default: settings.TOP_FINAL)

        Returns:
            List of Document objects sorted by reranker score (descending)
        """
        if top_k is None:
            top_k = settings.TOP_FINAL

        if not documents:
            return []

        if self.reranker is None:
            logger.warning("Reranker not available, returning documents as-is")
            return documents[:top_k]

        try:
            # Prepare query-document pairs for scoring
            pairs = [[query, doc.page_content] for doc in documents]

            # Compute reranker scores
            scores = self.reranker.compute_score(pairs)

            # Handle single score vs list of scores
            if isinstance(scores, (int, float)):
                scores = [scores]

            # Sort by score descending
            scored_docs = sorted(
                zip(documents, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # Update metadata with reranker scores and return top-k
            result = []
            for doc, score in scored_docs[:top_k]:
                doc.metadata['reranker_score'] = float(score)
                result.append(doc)

            logger.info(f"Reranker returned {len(result)} documents, top score: {scores[0]:.4f}")
            return result

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:top_k]


reranker_service = RerankerService()
```

- [ ] **Step 2: Commit**

```bash
git add backend/knowledge/services/reranker.py
git commit -m "feat: add bge-reranker service for document reranking"
```

---

### Task 15: Rewrite retrieval_service.py with hybrid pipeline

**Files:**
- Modify: `backend/knowledge/services/retrieval_service.py`

- [ ] **Step 1: Rewrite retrieval_service.py**

Replace the entire content of `backend/knowledge/services/retrieval_service.py`:

```python
import logging
import jieba
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from typing import List, Dict, Any
from langchain_core.documents import Document
from repositories.vector_store_repository import VectorStoreRepository
from services.ingestion.ingestion_processor import IngestionProcessor
from utils.markdown_utils import MarkDownUtils
from config.settings import settings
from sklearn.metrics.pairwise import cosine_similarity
from langfuse.decorators import observe


class RetrievalService:
    """
    RAG Retrieval Service with hybrid search pipeline.

    Pipeline:
    1. HyDE query rewriting (optional)
    2. Three-way retrieval: BM25 + Vector + Title
    3. Deduplication
    4. bge-reranker reranking
    5. Return top-K documents
    """

    def __init__(self):
        self.chroma_vector = VectorStoreRepository()
        self.spliter = IngestionProcessor()

        # Lazy-loaded components
        self._hyde_service = None
        self._bm25_retriever = None
        self._reranker_service = None

    @property
    def hyde_service(self):
        if self._hyde_service is None:
            from services.hyde import HyDEService
            self._hyde_service = HyDEService()
        return self._hyde_service

    @property
    def bm25_retriever(self):
        if self._bm25_retriever is None:
            from services.bm25_retriever import BM25Retriever
            self._bm25_retriever = BM25Retriever()
        return self._bm25_retriever

    @property
    def reranker_service(self):
        if self._reranker_service is None:
            from services.reranker import RerankerService
            self._reranker_service = RerankerService()
        return self._reranker_service

    @observe(as_type="retrieval", name="rag_retrieval")
    def retrieval(self, user_question: str) -> List[Document]:
        """
        Core retrieval method with hybrid search pipeline.

        Args:
            user_question: The user's question

        Returns:
            List of top-K relevant documents
        """
        # 1. HyDE: Generate hypothetical document for better vector search
        if settings.HYDE_ENABLED:
            search_query = self.hyde_service.generate_hypothetical_document(user_question)
        else:
            search_query = user_question

        # 2. Three-way retrieval
        # 2.1 BM25 keyword retrieval
        bm25_candidates = self._search_bm25(user_question)

        # 2.2 Vector retrieval (using HyDE query)
        vector_candidates = self._search_based_vector(search_query)

        # 2.3 Title-based retrieval (jieba)
        title_candidates = self._search_based_title(user_question)

        # 3. Merge all candidates
        all_candidates = bm25_candidates + vector_candidates + title_candidates
        logger.info(f"Retrieved {len(bm25_candidates)} BM25 + {len(vector_candidates)} vector + {len(title_candidates)} title = {len(all_candidates)} total")

        # 4. Deduplicate
        unique_candidates = self._deduplicate(all_candidates)
        logger.info(f"After dedup: {len(unique_candidates)} unique documents")

        if not unique_candidates:
            return []

        # 5. Rerank with bge-reranker
        if settings.RERANKER_ENABLED:
            top_documents = self.reranker_service.rerank(user_question, unique_candidates)
        else:
            # Fallback: cosine similarity reranking
            top_documents = self._cosine_rerank(user_question, unique_candidates)

        return top_documents

    def _search_bm25(self, user_question: str) -> List[Document]:
        """BM25 keyword retrieval."""
        return self.bm25_retriever.search(user_question, top_k=settings.TOP_K_BM25)

    def _search_based_vector(self, query: str) -> List[Document]:
        """Vector similarity retrieval."""
        documents_with_score = self.chroma_vector.search_similarity_with_score(query, top_k=settings.TOP_K_VECTOR)
        return [doc for doc, _ in documents_with_score]

    def _search_based_title(self, user_query: str) -> List[Document]:
        """Title-based retrieval with jieba matching."""
        mds_metadata = MarkDownUtils.collect_md_metadata(settings.CRAWL_OUTPUT_DIR)
        rough_mds_metadata = self.rough_ranking(user_query, mds_metadata)
        fine_mds_metadata = self.fine_ranking(user_query, rough_mds_metadata)

        based_title_candidates = []
        for fine_md_metadata in fine_mds_metadata:
            try:
                with open(fine_md_metadata['path'], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if len(content) < 3000:
                    doc = Document(page_content=content, metadata={
                        "path": fine_md_metadata['path'],
                        "title": fine_md_metadata['title'],
                    })
                    based_title_candidates.append(doc)
                else:
                    doc_chunks = self._deal_long_title_content(content, fine_md_metadata, user_query)
                    based_title_candidates.extend(doc_chunks)
            except Exception as e:
                logger.error(f"Failed to open file: {e}")
                continue

        return based_title_candidates

    def rough_ranking(self, user_query, mds_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rough ranking based on jieba title matching."""
        if not user_query:
            return []
        ROUGHIN_WORD_WEIGHT = 0.7

        for md_metadata in mds_metadata:
            md_metadata_title = md_metadata['title']
            if not md_metadata_title or not md_metadata_title.strip():
                continue

            user_query_char = set(user_query)
            md_metadata_title_char = set(md_metadata_title)
            unique_char = user_query_char | md_metadata_title_char
            char_score = len(user_query_char & md_metadata_title_char) / len(unique_char) if len(unique_char) > 0 else 0

            user_query_word = set(jieba.lcut(user_query))
            md_metadata_title_word = set(jieba.lcut(md_metadata_title))
            unique_word = user_query_word | md_metadata_title_word
            word_score = len(user_query_word & md_metadata_title_word) / len(unique_word) if len(unique_word) > 0 else 0

            roughing_score = word_score * ROUGHIN_WORD_WEIGHT + char_score * (1 - ROUGHIN_WORD_WEIGHT)
            md_metadata['roughing_score'] = float(roughing_score)

        return sorted(mds_metadata, key=lambda x: x['roughing_score'], reverse=True)[:50]

    def fine_ranking(self, user_query: str, rough_mds_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fine ranking based on embedding similarity."""
        if not rough_mds_metadata:
            return []

        query_embedding = self.chroma_vector.embedd_document(user_query)
        roughing_title = [md_metadata['title'] for md_metadata in rough_mds_metadata]
        roughing_title_embeddings = self.chroma_vector.embedd_documents(roughing_title)
        similarity = cosine_similarity([query_embedding], roughing_title_embeddings).flatten()

        ROUGH_HEIGHT = 0.3
        SIM_HEIGHT = 0.7
        for index, md_metadata in enumerate(rough_mds_metadata):
            sim = max(similarity[index], 0)
            roughing_score = md_metadata['roughing_score']
            final_score = roughing_score * ROUGH_HEIGHT + sim * SIM_HEIGHT
            md_metadata['sim_score'] = sim
            md_metadata['final_score'] = final_score

        return sorted(rough_mds_metadata, key=lambda x: x['final_score'], reverse=True)[:settings.TOP_K_TITLE]

    def _deduplicate(self, total_candidates: List[Document]) -> List[Document]:
        """Deduplicate documents by (title, first 100 chars)."""
        if not total_candidates:
            return []

        seen = set()
        unique_candidates = []
        for document in total_candidates:
            clean_content = re.sub(r'^文档来源:.*?(?=(\n|#))', '', document.page_content, flags=re.DOTALL).strip()
            key = (document.metadata.get('title', ''), clean_content[:100])
            if key not in seen:
                seen.add(key)
                unique_candidates.append(document)

        return unique_candidates

    def _cosine_rerank(self, user_question: str, unique_candidates: List[Document]) -> List[Document]:
        """Fallback cosine similarity reranking when reranker is not available."""
        if not unique_candidates:
            return []

        query_embedding = self.chroma_vector.embedd_document(user_question)
        doc_contents = [doc.page_content for doc in unique_candidates]
        doc_embeddings = self.chroma_vector.embedd_documents(doc_contents)
        similarity = cosine_similarity([query_embedding], doc_embeddings).flatten()

        scored_docs = sorted(zip(unique_candidates, similarity), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored_docs[:settings.TOP_FINAL]]

    def _deal_long_title_content(self, content: str, fine_md_metadata: Dict[str, Any], user_query: str) -> List[Document]:
        """Process long documents by chunking and selecting top-3 relevant chunks."""
        chunks = self.spliter.document_spliter.split_text(content)
        doc_chunks_title = fine_md_metadata['title']
        doc_chunks_inject_title = [f"文档来源:{doc_chunks_title}" + doc_chunk for doc_chunk in chunks]

        query_embedding = self.chroma_vector.embedd_document(user_query)
        doc_chunk_embeddings = self.chroma_vector.embedd_documents(doc_chunks_inject_title)
        doc_chunks_similarity = cosine_similarity([query_embedding], doc_chunk_embeddings).flatten()

        top_doc_chunks_indices = doc_chunks_similarity.argsort()[-3:][::-1]

        docs = []
        for chunk_idx in top_doc_chunks_indices:
            doc = Document(
                page_content=doc_chunks_inject_title[chunk_idx],
                metadata={
                    "path": fine_md_metadata['path'],
                    "title": fine_md_metadata['title'],
                    "chunk_index": int(chunk_idx),
                    "similarity": float(doc_chunks_similarity[chunk_idx])
                }
            )
            docs.append(doc)

        return docs


if __name__ == '__main__':
    retrival_service = RetrievalService()
    result = retrival_service.retrieval("手机、平板上的画面能无线传输到电视上播放吗")
    for r in result:
        print(r)
```

- [ ] **Step 2: Verify retrieval still works**

```bash
cd backend/knowledge && python -c "
from services.retrieval_service import RetrievalService
rs = RetrievalService()
results = rs.retrieval('电脑蓝屏怎么办')
print(f'Retrieved {len(results)} documents')
for r in results:
    print(f'  - {r.metadata.get(\"title\", \"N/A\")}')
"
```

Expected: Output shows retrieved documents with titles.

- [ ] **Step 3: Commit**

```bash
git add backend/knowledge/services/retrieval_service.py
git commit -m "feat: rewrite RAG retrieval with HyDE + BM25 + bge-reranker pipeline"
```

---

## Phase 4: Evaluation Framework

### Task 16: Create evaluation test cases

**Files:**
- Create: `backend/app/evaluation/__init__.py`
- Create: `backend/app/evaluation/test_cases.yaml`

- [ ] **Step 1: Create evaluation package**

Create `backend/app/evaluation/__init__.py`:

```python
```

- [ ] **Step 2: Create test cases file**

Create `backend/app/evaluation/test_cases.yaml`:

```yaml
# ITS Multi-Agent Evaluation Test Cases
# Categories: intent_recognition, rag_retrieval, multi_turn

# ============================================================
# Intent Recognition Tests
# ============================================================
- id: "intent_001"
  query: "我的电脑开机蓝屏怎么办"
  expected_intent: "technical"
  expected_agent: "consult_technical_expert"
  expected_keywords: ["蓝屏", "开机"]
  category: "intent_recognition"

- id: "intent_002"
  query: "帮我找一下附近的维修站"
  expected_intent: "service"
  expected_agent: "query_service_station_and_navigate"
  expected_keywords: ["维修", "服务站"]
  category: "intent_recognition"

- id: "intent_003"
  query: "今天北京天气怎么样"
  expected_intent: "technical"
  expected_agent: "consult_technical_expert"
  expected_keywords: ["天气"]
  category: "intent_recognition"

- id: "intent_004"
  query: "怎么去天安门广场"
  expected_intent: "service"
  expected_agent: "query_service_station_and_navigate"
  expected_keywords: ["天安门"]
  category: "intent_recognition"

- id: "intent_005"
  query: "查一下小米股价，然后导航去小米之家"
  expected_intent: "multi"
  expected_agents:
    - "consult_technical_expert"
    - "query_service_station_and_navigate"
  expected_keywords: ["小米"]
  category: "intent_recognition"

# ============================================================
# RAG Retrieval Tests
# ============================================================
- id: "rag_001"
  query: "如何使用U盘安装Windows 7操作系统"
  expected_keywords: ["U盘", "Windows 7", "安装"]
  category: "rag_retrieval"

- id: "rag_002"
  query: "电脑开机后没有任何反应怎么办"
  expected_keywords: ["开机", "反应", "电源"]
  category: "rag_retrieval"

- id: "rag_003"
  query: "手机平板画面无线传输到电视"
  expected_keywords: ["无线", "传输", "电视"]
  category: "rag_retrieval"

- id: "rag_004"
  query: "电脑经常死机如何解决"
  expected_keywords: ["死机", "内存", "散热"]
  category: "rag_retrieval"

- id: "rag_005"
  query: "Windows系统如何还原"
  expected_keywords: ["还原", "系统", "恢复"]
  category: "rag_retrieval"

# ============================================================
# Multi-turn Conversation Tests
# ============================================================
- id: "multi_turn_001"
  turns:
    - role: "user"
      content: "我的电脑开不了机"
    - role: "assistant"
      content: "请检查电源线是否连接正常，尝试更换电源插座..."
    - role: "user"
      content: "试了还是不行，帮我找最近的维修站"
  expected_intent: "service"
  expected_agent: "query_service_station_and_navigate"
  category: "multi_turn"

- id: "multi_turn_002"
  turns:
    - role: "user"
      content: "电脑蓝屏了"
    - role: "assistant"
      content: "蓝屏通常由以下原因导致..."
    - role: "user"
      content: "那个错误代码是什么意思"
  expected_intent: "technical"
  expected_agent: "consult_technical_expert"
  category: "multi_turn"

- id: "multi_turn_003"
  turns:
    - role: "user"
      content: "帮我查一下故宫今天开不开门"
    - role: "assistant"
      content: "故宫今天开放..."
    - role: "user"
      content: "那帮我导航过去"
  expected_intent: "service"
  expected_agent: "query_service_station_and_navigate"
  category: "multi_turn"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/evaluation/
git commit -m "feat: add evaluation test cases (intent, RAG, multi-turn)"
```

---

### Task 17: Create LLM-as-Judge

**Files:**
- Create: `backend/app/evaluation/judge.py`

- [ ] **Step 1: Create judge module**

Create `backend/app/evaluation/judge.py`:

```python
import json
import logging
from typing import Dict, Optional
from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-as-Judge for automated evaluation of agent outputs.
    Scores across 5 dimensions: intent, relevance, completeness, rag_quality, coherence.
    """

    JUDGE_PROMPT = """你是一个AI系统评测专家。请根据以下信息对Agent的回答进行评分。

## 用户问题
{query}

## Agent回答
{answer}

## 检索文档（如有）
{retrieved_docs}

## 评分维度（每项0-10分）

1. **意图识别准确性** (intent): Agent是否正确理解了用户意图并调用了合适的工具
2. **回答相关性** (relevance): 回答内容是否与用户问题相关
3. **回答完整性** (completeness): 回答是否完整覆盖了问题的要点
4. **RAG检索质量** (rag_quality): 检索到的文档是否与问题相关、是否有用
5. **多轮对话连贯性** (coherence): 是否正确理解了上下文中的引用和指代

请严格按以下JSON格式输出，不要添加任何其他内容：
{{"intent": 分数, "relevance": 分数, "completeness": 分数, "rag_quality": 分数, "coherence": 分数, "reasoning": "简要说明评分理由"}}"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.SUB_API_KEY,
            base_url=settings.SUB_BASE_URL,
        )
        self.model = settings.SUB_MODEL_NAME

    async def evaluate(
        self,
        query: str,
        answer: str,
        retrieved_docs: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Evaluate an agent's answer using LLM-as-Judge.

        Args:
            query: The original user query
            answer: The agent's answer
            retrieved_docs: Optional string of retrieved documents

        Returns:
            Dict with scores for each dimension and reasoning
        """
        docs_text = retrieved_docs if retrieved_docs else "无检索文档"

        prompt = self.JUDGE_PROMPT.format(
            query=query,
            answer=answer,
            retrieved_docs=docs_text,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response
            if "{" in result_text:
                json_start = result_text.index("{")
                json_end = result_text.rindex("}") + 1
                result_text = result_text[json_start:json_end]

            scores = json.loads(result_text)

            # Validate scores
            valid_dimensions = ["intent", "relevance", "completeness", "rag_quality", "coherence"]
            for dim in valid_dimensions:
                if dim not in scores:
                    scores[dim] = 0.0
                else:
                    scores[dim] = float(max(0, min(10, scores[dim])))

            return scores

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse judge response as JSON: {e}")
            return {"intent": 0, "relevance": 0, "completeness": 0, "rag_quality": 0, "coherence": 0, "reasoning": "JSON解析失败"}
        except Exception as e:
            logger.error(f"LLM judge evaluation failed: {e}")
            return {"intent": 0, "relevance": 0, "completeness": 0, "rag_quality": 0, "coherence": 0, "reasoning": f"评估失败: {str(e)}"}


llm_judge = LLMJudge()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/evaluation/judge.py
git commit -m "feat: add LLM-as-Judge for automated evaluation scoring"
```

---

### Task 18: Create evaluation runner

**Files:**
- Create: `backend/app/evaluation/runner.py`

- [ ] **Step 1: Create evaluation runner**

Create `backend/app/evaluation/runner.py`:

```python
import asyncio
import time
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any

from langfuse.decorators import observe
from infrastructure.observability.langfuse_client import langfuse, flush_langfuse
from evaluation.judge import llm_judge

logger = logging.getLogger(__name__)

TEST_CASES_PATH = Path(__file__).parent / "test_cases.yaml"


def load_test_cases() -> List[Dict[str, Any]]:
    """Load test cases from YAML file."""
    with open(TEST_CASES_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@observe(as_type="agent", name="evaluation_runner")
async def run_single_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single test case through the agent and evaluate with LLM judge.

    Args:
        test_case: Test case dictionary from YAML

    Returns:
        Dict with test results including scores and latency
    """
    case_id = test_case["id"]
    category = test_case["category"]

    start_time = time.time()

    try:
        if category == "multi_turn":
            # For multi-turn, use the last user message as query
            query = test_case["turns"][-1]["content"]
            # Build chat history from turns
            chat_history = []
            for turn in test_case["turns"]:
                chat_history.append({"role": turn["role"], "content": turn["content"]})
        else:
            query = test_case["query"]
            chat_history = None

        # Run the agent
        from services.agent_service import MultiAgentService
        from schemas.request import ChatMessageRequest, UserContext

        request = ChatMessageRequest(
            query=query,
            context=UserContext(user_id="eval_user", session_id=f"eval_{case_id}"),
            flag=False,
        )

        # Collect SSE output
        answer_parts = []
        async for chunk in MultiAgentService.process_task(request, flag=False):
            # Extract text from SSE data
            if "data:" in chunk:
                try:
                    import json
                    data_str = chunk.split("data:", 1)[1].strip()
                    data = json.loads(data_str)
                    if data.get("kind") == "ANSWER":
                        answer_parts.append(data.get("content", ""))
                except:
                    pass

        answer = "".join(answer_parts)
        latency = time.time() - start_time

        # Evaluate with LLM judge
        scores = await llm_judge.evaluate(query=query, answer=answer)

        return {
            "case_id": case_id,
            "category": category,
            "query": query,
            "answer": answer[:500],
            "scores": scores,
            "latency": round(latency, 2),
            "success": True,
        }

    except Exception as e:
        logger.error(f"Test case {case_id} failed: {e}")
        return {
            "case_id": case_id,
            "category": category,
            "query": test_case.get("query", ""),
            "answer": "",
            "scores": {},
            "latency": round(time.time() - start_time, 2),
            "success": False,
            "error": str(e),
        }


async def run_evaluation():
    """
    Run all test cases and write scores to Langfuse.

    Returns:
        Dict with summary statistics
    """
    test_cases = load_test_cases()
    logger.info(f"Running {len(test_cases)} evaluation cases...")

    results = []
    for test_case in test_cases:
        logger.info(f"Running case: {test_case['id']}")
        result = await run_single_case(test_case)
        results.append(result)

        # Write scores to Langfuse
        if result["success"] and result["scores"]:
            for dimension, score in result["scores"].items():
                if dimension == "reasoning":
                    continue
                try:
                    langfuse.score(
                        name=dimension,
                        value=score,
                        comment=result["scores"].get("reasoning", ""),
                    )
                except Exception as e:
                    logger.warning(f"Failed to write Langfuse score: {e}")

    flush_langfuse()

    # Compute summary
    successful = [r for r in results if r["success"]]
    summary = {
        "total_cases": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
    }

    if successful:
        # Average scores per dimension
        dimensions = ["intent", "relevance", "completeness", "rag_quality", "coherence"]
        for dim in dimensions:
            scores = [r["scores"].get(dim, 0) for r in successful if r["scores"]]
            if scores:
                summary[f"avg_{dim}"] = round(sum(scores) / len(scores), 2)

        # Average latency
        latencies = [r["latency"] for r in successful]
        summary["avg_latency"] = round(sum(latencies) / len(latencies), 2)

        # Per-category breakdown
        for category in ["intent_recognition", "rag_retrieval", "multi_turn"]:
            cat_results = [r for r in successful if r["category"] == category]
            if cat_results:
                summary[f"{category}_count"] = len(cat_results)
                cat_scores = [r["scores"].get("intent", 0) for r in cat_results if r["scores"]]
                if cat_scores:
                    summary[f"{category}_avg_intent"] = round(sum(cat_scores) / len(cat_scores), 2)

    return {"results": results, "summary": summary}


if __name__ == "__main__":
    result = asyncio.run(run_evaluation())
    print("\n" + "=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    for key, value in result["summary"].items():
        print(f"  {key}: {value}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/evaluation/runner.py
git commit -m "feat: add evaluation runner with Langfuse score integration"
```

---

## Final Verification

### Task 19: Install all dependencies and verify imports

- [ ] **Step 1: Install backend/app dependencies**

```bash
cd backend/app && pip install -r requirements.txt
```

- [ ] **Step 2: Install backend/knowledge dependencies**

```bash
cd backend/knowledge && pip install -r requirements.txt
```

- [ ] **Step 3: Verify Python imports**

```bash
cd backend/app && python -c "
from infrastructure.observability.langfuse_client import langfuse, flush_langfuse
from evaluation.judge import llm_judge
from evaluation.runner import run_evaluation
print('All imports successful')
"
```

- [ ] **Step 4: Verify knowledge service imports**

```bash
cd backend/knowledge && python -c "
from services.hyde import HyDEService
from services.bm25_retriever import BM25Retriever
from services.reranker import RerankerService
from services.retrieval_service import RetrievalService
print('All knowledge imports successful')
"
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: P0 upgrade complete - Langfuse, multi-turn fix, RAG optimization"
```
