"""
RAG 检索质量评测模块
使用 RAGAS 框架评估 RAG 系统的 Context Precision、Context Recall、Faithfulness、Answer Relevancy
并将评测结果写入 Langfuse。
"""

import asyncio
import logging
import time
import yaml
import httpx
from pathlib import Path
from typing import List, Dict, Any

from datasets import Dataset
from ragas import evaluate
from ragas.metrics.collections import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)

from langfuse import observe
from infrastructure.observability.langfuse_client import langfuse, flush_langfuse
from config.settings import settings

logger = logging.getLogger(__name__)

TEST_CASES_PATH = Path(__file__).parent / "test_cases_rag.yaml"
KNOWLEDGE_API = settings.KNOWLEDGE_BASE_URL or "http://127.0.0.1:8001"


def load_rag_test_cases() -> List[Dict[str, Any]]:
    """加载 RAG 评测用例。"""
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def query_knowledge_service(question: str) -> Dict[str, Any]:
    """
    调用知识库服务获取回答和检索上下文。

    Args:
        question: 用户问题

    Returns:
        Dict with answer and contexts
    """
    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        # 调用知识库查询接口
        resp = await client.post(
            f"{KNOWLEDGE_API}/query",
            json={"question": question},
        )
        resp.raise_for_status()
        data = resp.json()

        answer = data.get("answer", "")

        # 调用检索接口获取原始 contexts
        retrieval_resp = await client.post(
            f"{KNOWLEDGE_API}/retrieval",
            json={"question": question},
        )
        contexts = []
        if retrieval_resp.status_code == 200:
            retrieval_data = retrieval_resp.json()
            contexts = retrieval_data.get("contexts", [])

        return {"answer": answer, "contexts": contexts}


@observe(as_type="agent", name="rag_evaluation")
async def run_single_rag_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行单条 RAG 评测用例。

    Args:
        test_case: 评测用例（包含 question 和 ground_truth）

    Returns:
        评测结果
    """
    case_id = test_case["id"]
    question = test_case["question"]
    ground_truth = test_case["ground_truth"]

    start_time = time.time()

    try:
        # 1. 调用知识库服务
        result = await query_knowledge_service(question)
        answer = result["answer"]
        contexts = result["contexts"]

        # 如果没有获取到 contexts，用 answer 作为 fallback
        if not contexts:
            contexts = [answer] if answer else ["无检索结果"]

        latency = time.time() - start_time

        return {
            "case_id": case_id,
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": ground_truth,
            "latency": round(latency, 2),
            "success": True,
        }

    except Exception as e:
        logger.error(f"RAG 评测用例 {case_id} 失败: {e}")
        return {
            "case_id": case_id,
            "question": question,
            "answer": "",
            "contexts": [],
            "ground_truth": ground_truth,
            "latency": round(time.time() - start_time, 2),
            "success": False,
            "error": str(e),
        }


def compute_ragas_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    使用 RAGAS 计算评测指标。

    Args:
        results: 评测结果列表（成功的用例）

    Returns:
        各指标的平均分
    """
    # 构造 RAGAS 需要的 Dataset
    questions = []
    answers = []
    contexts_list = []
    ground_truths = []

    for r in results:
        questions.append(r["question"])
        answers.append(r["answer"])
        contexts_list.append(r["contexts"])
        ground_truths.append(r["ground_truth"])

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    })

    # 运行 RAGAS 评测
    result = evaluate(
        dataset=dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
    )

    return result


async def run_rag_evaluation():
    """
    运行完整的 RAG 评测流程。

    Returns:
        评测结果和汇总统计
    """
    test_cases = load_rag_test_cases()
    logger.info(f"开始 RAG 评测，共 {len(test_cases)} 条用例...")

    # 1. 逐条运行评测用例
    results = []
    for test_case in test_cases:
        logger.info(f"运行用例: {test_case['id']} - {test_case['question'][:30]}...")
        result = await run_single_rag_case(test_case)
        results.append(result)

    # 2. 筛选成功的用例
    successful = [r for r in results if r["success"] and r["answer"]]
    logger.info(f"成功: {len(successful)}/{len(results)}")

    if not successful:
        logger.error("没有成功的评测用例，无法计算 RAGAS 指标")
        return {"results": results, "summary": {"error": "no successful cases"}}

    # 3. 使用 RAGAS 计算指标
    logger.info("正在计算 RAGAS 指标...")
    ragas_result = compute_ragas_scores(successful)

    # 4. 提取各指标平均分
    summary = {
        "total_cases": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
    }

    # RAGAS 返回的指标
    metric_names = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
    for metric in metric_names:
        if metric in ragas_result:
            summary[f"avg_{metric}"] = round(ragas_result[metric], 4)

    # 平均延迟
    latencies = [r["latency"] for r in successful]
    summary["avg_latency"] = round(sum(latencies) / len(latencies), 2)

    # 5. 写入 Langfuse
    for metric in metric_names:
        if metric in ragas_result:
            try:
                langfuse.score(
                    name=f"rag_{metric}",
                    value=round(ragas_result[metric] * 10, 2),  # 转为 0-10 分制
                    comment=f"RAG 评测 - {metric}: {ragas_result[metric]:.4f}",
                )
            except Exception as e:
                logger.warning(f"写入 Langfuse 失败: {e}")

    flush_langfuse()

    # 6. 逐条结果也写入 Langfuse
    for i, r in enumerate(successful):
        if i < len(ragas_result.get("context_precision", [])):
            try:
                langfuse.score(
                    name="rag_case_detail",
                    value=round(ragas_result["context_precision"][i] * 10, 2),
                    comment=f"用例: {r['question'][:50]}",
                )
            except Exception:
                pass

    return {"results": results, "summary": summary, "ragas_raw": ragas_result}


if __name__ == "__main__":
    result = asyncio.run(run_rag_evaluation())
    print("\n" + "=" * 60)
    print("RAG 评测结果")
    print("=" * 60)
    for key, value in result["summary"].items():
        print(f"  {key}: {value}")
