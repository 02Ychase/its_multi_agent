import asyncio
import time
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any

from langfuse import observe
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
