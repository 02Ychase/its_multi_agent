import os
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
from langfuse import observe
from services.query_router import classify_query, decompose_query, QueryComplexity


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
        # 标题元数据缓存
        self._title_metadata_cache = None
        self._title_cache_hash = None

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

    @observe(as_type="retriever", name="rag_retrieval")
    def retrieval(self, user_question: str) -> List[Document]:
        # 0. 查询路由
        complexity = classify_query(user_question)

        if complexity == QueryComplexity.SIMPLE:
            return self._retrieval_simple(user_question)
        elif complexity == QueryComplexity.COMPLEX:
            return self._retrieval_complex(user_question)
        else:
            return self._retrieval_standard(user_question)

    def _retrieval_simple(self, user_question: str) -> List[Document]:
        """简单查询：跳过 HyDE，直接检索。"""
        bm25_candidates = self._search_bm25(user_question)
        vector_candidates = self._search_based_vector(user_question)
        title_candidates = self._search_based_title(user_question)
        all_candidates = bm25_candidates + vector_candidates + title_candidates
        unique_candidates = self._deduplicate(all_candidates)
        if not unique_candidates:
            return []
        if settings.RERANKER_ENABLED:
            return self.reranker_service.rerank(user_question, unique_candidates)
        return self._cosine_rerank(user_question, unique_candidates)

    def _retrieval_standard(self, user_question: str) -> List[Document]:
        """标准查询：完整 HyDE + 三路检索 + 重排（原有逻辑）。"""
        if settings.HYDE_ENABLED:
            search_query = self.hyde_service.generate_hypothetical_document(user_question)
        else:
            search_query = user_question
        bm25_candidates = self._search_bm25(user_question)
        vector_candidates = self._search_based_vector(search_query)
        title_candidates = self._search_based_title(user_question)
        all_candidates = bm25_candidates + vector_candidates + title_candidates
        unique_candidates = self._deduplicate(all_candidates)
        if not unique_candidates:
            return []
        if settings.RERANKER_ENABLED:
            return self.reranker_service.rerank(user_question, unique_candidates)
        return self._cosine_rerank(user_question, unique_candidates)

    def _retrieval_complex(self, user_question: str) -> List[Document]:
        """复杂查询：分解为子查询，分别检索后合并。"""
        sub_queries = decompose_query(user_question)
        all_candidates = []
        for sub_q in sub_queries:
            bm25_candidates = self._search_bm25(sub_q)
            vector_candidates = self._search_based_vector(sub_q)
            all_candidates.extend(bm25_candidates + vector_candidates)
        title_candidates = self._search_based_title(user_question)
        all_candidates.extend(title_candidates)
        unique_candidates = self._deduplicate(all_candidates)
        if not unique_candidates:
            return []
        if settings.RERANKER_ENABLED:
            return self.reranker_service.rerank(user_question, unique_candidates)
        return self._cosine_rerank(user_question, unique_candidates)

    def _search_bm25(self, user_question: str) -> List[Document]:
        """BM25 keyword retrieval."""
        return self.bm25_retriever.search(user_question, top_k=settings.TOP_K_BM25)

    def _search_based_vector(self, query: str) -> List[Document]:
        """Vector similarity retrieval."""
        documents_with_score = self.chroma_vector.search_similarity_with_score(query, top_k=5)
        return [doc for doc, _ in documents_with_score]

    def _get_cached_title_metadata(self):
        """获取标题元数据，优先从缓存读取。"""
        import hashlib
        current_hash = self._compute_dir_hash(settings.CRAWL_OUTPUT_DIR)
        if self._title_metadata_cache is not None and self._title_cache_hash == current_hash:
            return [dict(m) for m in self._title_metadata_cache]
        self._title_metadata_cache = MarkDownUtils.collect_md_metadata(settings.CRAWL_OUTPUT_DIR)
        self._title_cache_hash = current_hash
        logger.info(f"Title metadata cache refreshed: {len(self._title_metadata_cache)} entries")
        return [dict(m) for m in self._title_metadata_cache]

    def _compute_dir_hash(self, dir_path: str) -> str:
        import hashlib
        hasher = hashlib.md5()
        if not os.path.exists(dir_path):
            return ""
        for fname in sorted(os.listdir(dir_path)):
            fpath = os.path.join(dir_path, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                hasher.update(f"{fname}:{stat.st_size}:{stat.st_mtime}".encode())
        return hasher.hexdigest()

    def _search_based_title(self, user_query: str) -> List[Document]:
        """Title-based retrieval with caching."""
        mds_metadata = self._get_cached_title_metadata()
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
