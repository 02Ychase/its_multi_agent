import os.path
from pathlib import Path

from repositories.vector_store_repository import VectorStoreRepository
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
        self.document_spliter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=[
                "\n## ",
                "\n**",
                "\n\n",
                "\n",
                " ",
                ""
            ]
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

        # 3. 切分文档（动态策略：短文档不切，长文档分块 + 标题注入）
        final_document_chunks = []
        for doc in documents:
            if len(doc.page_content) < 3000:
                final_document_chunks.append(doc)
            else:
                documents_chunks_list = self.document_spliter.split_documents(documents)
                for document_chunk in documents_chunks_list:
                    source = document_chunk.metadata.get('source', file_path)
                    title = os.path.basename(source)
                    document_chunk.page_content = f"文档来源:{title}\n{document_chunk.page_content}"
                final_document_chunks.extend(documents_chunks_list)

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







