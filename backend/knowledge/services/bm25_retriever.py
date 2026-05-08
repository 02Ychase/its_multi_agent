import os
import logging
import jieba
from pathlib import Path
from typing import List
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from config.settings import settings

# 支持的文件格式
SUPPORTED_EXTENSIONS = {'.md', '.txt', '.docx', '.pdf'}

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

    def _read_file_content(self, file_path: str) -> str:
        """根据文件格式读取内容，统一返回纯文本。"""
        ext = Path(file_path).suffix.lower()

        if ext in ('.md', '.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()

        elif ext == '.pdf':
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            return result.document.export_to_markdown().strip()

        elif ext == '.docx':
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            return result.document.export_to_markdown().strip()

        return ""

    def _build_index(self):
        """Build BM25 index from all supported files in crawl and uploaded directories."""
        dirs_to_scan = [
            settings.CRAWL_OUTPUT_DIR,
            os.path.join(settings._project_root, "data", "uploaded"),
        ]

        tokenized_corpus = []
        for scan_dir in dirs_to_scan:
            if not os.path.exists(scan_dir):
                continue

            files = [f for f in os.listdir(scan_dir)
                     if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
            for file_name in files:
                file_path = os.path.join(scan_dir, file_name)
                try:
                    content = self._read_file_content(file_path)
                    if not content:
                        continue

                    title = os.path.splitext(file_name)[0]
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
