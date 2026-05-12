import os
import pickle
import hashlib
import logging
import jieba
from pathlib import Path
from typing import List
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from config.settings import settings

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.docx', '.pdf'}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 索引文件存储路径
BM25_INDEX_PATH = os.path.join(settings._project_root, "data", "bm25_index.pkl")
BM25_HASH_PATH = os.path.join(settings._project_root, "data", "bm25_hash.txt")


class BM25Retriever:
    """
    BM25 keyword-based retriever with persistent index.
    Index is rebuilt only when document files change (based on directory hash).
    """

    def __init__(self):
        self.corpus_texts: List[str] = []
        self.corpus_paths: List[str] = []
        self.corpus_titles: List[str] = []
        self.bm25: BM25Okapi | None = None

        current_hash = self._compute_directory_hash()
        if self._try_load_index(current_hash):
            logger.info("BM25 index loaded from disk cache")
        else:
            self._build_index()
            self._save_index(current_hash)

    def _compute_directory_hash(self) -> str:
        """
        计算文档目录的指纹：基于所有文件名 + 文件大小 + 修改时间。
        任何文件的增删改都会导致 hash 变化，从而触发索引重建。
        """
        hasher = hashlib.md5()
        dirs_to_scan = [
            settings.CRAWL_OUTPUT_DIR,
            os.path.join(settings._project_root, "data", "uploaded"),
        ]
        for scan_dir in sorted(dirs_to_scan):
            if not os.path.exists(scan_dir):
                continue
            for fname in sorted(os.listdir(scan_dir)):
                if Path(fname).suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                fpath = os.path.join(scan_dir, fname)
                stat = os.stat(fpath)
                hasher.update(f"{fpath}:{stat.st_size}:{stat.st_mtime}".encode())
        return hasher.hexdigest()

    def _try_load_index(self, current_hash: str) -> bool:
        """尝试从磁盘加载已有索引，如果 hash 一致则加载成功。"""
        if not os.path.exists(BM25_INDEX_PATH) or not os.path.exists(BM25_HASH_PATH):
            return False
        try:
            with open(BM25_HASH_PATH, "r") as f:
                saved_hash = f.read().strip()
            if saved_hash != current_hash:
                logger.info("Document files changed, will rebuild BM25 index")
                return False
            with open(BM25_INDEX_PATH, "rb") as f:
                data = pickle.load(f)
            self.corpus_texts = data["corpus_texts"]
            self.corpus_paths = data["corpus_paths"]
            self.corpus_titles = data["corpus_titles"]
            self.bm25 = data["bm25"]
            return True
        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}")
            return False

    def _save_index(self, current_hash: str):
        """将构建完成的索引序列化到磁盘。"""
        try:
            os.makedirs(os.path.dirname(BM25_INDEX_PATH), exist_ok=True)
            data = {
                "corpus_texts": self.corpus_texts,
                "corpus_paths": self.corpus_paths,
                "corpus_titles": self.corpus_titles,
                "bm25": self.bm25,
            }
            with open(BM25_INDEX_PATH, "wb") as f:
                pickle.dump(data, f)
            with open(BM25_HASH_PATH, "w") as f:
                f.write(current_hash)
            logger.info(f"BM25 index saved to {BM25_INDEX_PATH}")
        except Exception as e:
            logger.warning(f"Failed to save BM25 index: {e}")

    def rebuild_index(self):
        """公开方法：强制重建索引（文档上传后调用）。"""
        self.corpus_texts.clear()
        self.corpus_paths.clear()
        self.corpus_titles.clear()
        self.bm25 = None
        self._build_index()
        self._save_index(self._compute_directory_hash())

    def _read_file_content(self, file_path: str) -> str:
        """根据文件格式读取内容。"""
        ext = Path(file_path).suffix.lower()
        if ext in ('.md', '.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        elif ext in ('.pdf', '.docx'):
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            return result.document.export_to_markdown().strip()
        return ""

    def _build_index(self):
        """从磁盘文件构建 BM25 索引。"""
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
                    if '-' in title:
                        title = title.split('-', 1)[1]
                    self.corpus_texts.append(content)
                    self.corpus_paths.append(file_path)
                    self.corpus_titles.append(title)
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
        """BM25 检索，与原逻辑完全相同。"""
        if self.bm25 is None or not self.corpus_texts:
            return []
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
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
