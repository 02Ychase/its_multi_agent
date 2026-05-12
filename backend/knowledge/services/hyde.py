import logging

from config.settings import settings
from langchain_openai import ChatOpenAI

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
