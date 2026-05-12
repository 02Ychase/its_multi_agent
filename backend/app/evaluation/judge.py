import json
import logging

from config.settings import settings
from openai import AsyncOpenAI

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
        retrieved_docs: str | None = None,
    ) -> dict[str, float]:
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
