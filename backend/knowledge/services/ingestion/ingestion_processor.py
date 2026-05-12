import os.path
from pathlib import Path

from repositories.vector_store_repository import VectorStoreRepository
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata
from utils.markdown_utils import MarkDownUtils
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 支持的文件格式
SUPPORTED_EXTENSIONS = {'.md', '.txt', '.docx', '.pdf'}

class IngestionProcessor:
    """
    文档摄入类：（摄入：加载、切分、存储）
    支持格式：.md, .txt, .docx, .pdf
    """

    def __init__(self):
        self.vector_store = VectorStoreRepository()

        # Markdown 语义分块器：按标题层级切分
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
            ],
            strip_headers=False,  # 保留标题文本在块内容中
        )

        # 二级分块器：对语义分块后仍过长的块做字符级切分
        self.document_spliter = RecursiveCharacterTextSplitter(
            chunk_size=1000,        # 从 1500 降低到 1000
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def _load_file(self, file_path: str) -> list[Document]:
        """
        根据文件后缀选择合适的加载器，统一返回 List[Document]。

        Args:
            file_path: 文件路径

        Returns:
            List[Document]: 加载后的文档列表
        """
        ext = Path(file_path).suffix.lower()

        if ext in ('.md', '.txt'):
            # Markdown / 纯文本：用 TextLoader
            loader = TextLoader(file_path=file_path, encoding="utf-8")
            return loader.load()

        elif ext == '.pdf':
            # PDF：用 docling 解析
            return self._load_with_docling(file_path)

        elif ext == '.docx':
            # Word 文档：用 docling 解析
            return self._load_with_docling(file_path)

        else:
            raise ValueError(f"不支持的文件格式: {ext}，支持的格式: {SUPPORTED_EXTENSIONS}")

    def _load_with_docling(self, file_path: str) -> list[Document]:
        """
        使用 docling 解析 PDF / DOCX 文件，输出结构化 Markdown。

        Args:
            file_path: 文件路径

        Returns:
            List[Document]: 解析后的文档列表（单个文档）
        """
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)
        markdown_text = result.document.export_to_markdown()

        doc = Document(
            page_content=markdown_text,
            metadata={"source": file_path}
        )
        logger.info(f"docling 解析完成: {file_path}, 文本长度: {len(markdown_text)}")
        return [doc]

    def ingest_file(self, file_path: str) -> int:
        """
        文档完整操作：加载 → 切分 → 存储
        Args:
            file_path: 文件的路径

        Returns:
            int: 保存成功的文档块数
        """
        # 1. 根据文件格式加载文档
        try:
            documents = self._load_file(file_path)
        except Exception as e:
            logger.error(f"文件：{file_path} 没有加载到, 原因: {str(e)}")
            raise Exception(f"文件：{file_path} 没有加载到, 原因: {str(e)}")

        # 2. 提取标题并注入元数据
        for doc in documents:
            doc.metadata['title'] = MarkDownUtils.extract_title(file_path)

        # 3. 切分文档（语义分块 + 二级字符分块）
        final_document_chunks = []
        for doc in documents:
            ext = Path(file_path).suffix.lower()
            content = doc.page_content
            title = doc.metadata.get('title', '')

            if ext == '.md' and len(content) >= 500:
                # Markdown 文件：先按标题语义切分
                md_chunks = self.markdown_splitter.split_text(content)
                for md_chunk in md_chunks:
                    chunk_text = md_chunk.page_content
                    chunk_metadata = {**doc.metadata, **md_chunk.metadata}
                    if len(chunk_text) > 1200:
                        # 语义块太长，再做字符级切分
                        sub_chunks = self.document_spliter.split_text(chunk_text)
                        for i, sub in enumerate(sub_chunks):
                            sub_doc = Document(
                                page_content=f"文档来源:{title}\n{sub}",
                                metadata={**chunk_metadata, "chunk_index": i}
                            )
                            final_document_chunks.append(sub_doc)
                    else:
                        final_document_chunks.append(Document(
                            page_content=f"文档来源:{title}\n{chunk_text}",
                            metadata=chunk_metadata
                        ))
            elif len(content) < 1200:
                # 短文档不切分
                final_document_chunks.append(doc)
            else:
                # 非 Markdown 或无标题结构的长文档：字符级切分
                chunks = self.document_spliter.split_documents([doc])
                for chunk in chunks:
                    chunk.page_content = f"文档来源:{title}\n{chunk.page_content}"
                final_document_chunks.extend(chunks)

        # 4. 过滤不被向量数据库支持的元数据
        clean_documents_chunks = filter_complex_metadata(final_document_chunks)

        # 5. 无效性检查
        valid_documents_chunks = [doc for doc in clean_documents_chunks if doc.page_content.strip()]
        if not valid_documents_chunks:
            logger.error("切分后的文档块没有任何的内容")
            return 0

        # 6. 存储到向量数据库
        total_documents_chunks = self.vector_store.add_documents(valid_documents_chunks)
        return total_documents_chunks


if __name__ == '__main__':
    ingest_processor = IngestionProcessor()
    ingest_processor.ingest_file("C:\\Users\\Administrator\\Desktop\\test.md")







