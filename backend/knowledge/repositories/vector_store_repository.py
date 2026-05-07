# 1. 优先import

import  logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)


# 2. from三方的
from langchain_chroma import Chroma
from config.settings import settings
from langchain_core.documents import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from typing import List

# 3. from 自己的



class VectorStoreRepository:
    """
     作用：对向量数据库做场景读写

    """

    def __init__(self):
        """
        创建向量数据库实例
        创建嵌入模型的实例
        向量数据库能力: 1.存储向量数据 2.搜索能力（向量数据库检索器）
        """
        # 使用API嵌入模型，配置从.env读取
        self.embedding = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.BASE_URL,
            check_embedding_ctx_length=False  # 兼容DashScope API格式
        )

        self.vector_database = Chroma(
            persist_directory=settings.VECTOR_STORE_PATH,
            collection_name="its-knowledge",
            embedding_function=self.embedding
        )


    def  add_documents(self,documents:list,batch_size:int=10)->int:
        """
        将切分之后的文档块保存到向量数据库中

        Args:
            documents: 切分之后的文档块
            batch_size: 分批保存文档块的批次大小（DashScope限制最大10）

        Returns:
            int:成功添加到向量数据库中文档块的数量(服务前端展示)

        """

        # 1. 获取到文档块的总数量
        total_documents_chunks=len(documents)

        # 2. 分批次保存
        documents_chunks_added=0
        try:
            for i in range(0,total_documents_chunks,batch_size):
                bath=documents[i:i+batch_size]
                self.vector_database.add_documents(bath)
                documents_chunks_added=documents_chunks_added+len(bath)
                logger.info(f"成功将文档块:{documents_chunks_added}/{total_documents_chunks}保存到向量数据库...")
            return documents_chunks_added
        except Exception as e:
            logger.error(f"文档块列表:{documents}保存到向量数据库失败: {str(e)}")
            raise e



    def    embedd_document(self,text:str)->List[float]:
        """
          对query进行向量化
        Args:
            text: 输入文本

        Returns:
            List[float]: 嵌入后的浮点数列表

        """
        return self.embedding.embed_query(text)

    def embedd_documents(self, texts:List[str], batch_size:int=10)->List[List[float]]:
        """
        对字符串列表进行向量化（分批处理，兼容DashScope API限制）
        Args:
         texts: 输入文本字符串列表
         batch_size: 每批处理数量（DashScope限制最大10）

        Returns:
            List[List[float]]: 嵌入后的多个文本的浮点数列表

        """
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.embedding.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        return all_embeddings


    def  search_similarity_with_score(self,user_question:str,top_k:int=5)->List[tuple[Document, float]]:
        """
         相似性检索带文档分数
         分数（chroma向量数据库）：返回是L2距离得分（分数值越小越相似），不是余弦相似度的得分（分数余额高越相似） 距离得分：1-余弦相似度得分
        Args:
            user_question:

        Returns:
            List[Document]: 返回基于向量检索的相似性文档列表

        """
        return self.vector_database.similarity_search_with_score(user_question,top_k)





















