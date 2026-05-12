"""
查询路由器：根据查询复杂度选择不同的检索策略。

策略：
- SIMPLE: 跳过 HyDE，直接三路检索 + 重排
- STANDARD: 完整管线（HyDE + 三路检索 + 重排）
- COMPLEX: 查询分解为子查询，分别检索后合并去重 + 重排
"""

import logging
import re
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


# 简单查询的特征：短查询、单一主题
SIMPLE_INDICATORS = [
    lambda q: len(q) < 15,                          # 短于 15 字符
    lambda q: "怎么" in q and len(q) < 25,           # 简单的 "怎么" 问题
    lambda q: q.count("？") <= 1 and len(q) < 30,    # 单个问号且短
]

# 复杂查询的特征：多个问题、条件、比较
COMPLEX_INDICATORS = [
    lambda q: q.count("？") >= 2,                     # 多个问号
    lambda q: bool(re.search(r"(如果|假如|假设).+(那么|就|则)", q)),  # 条件句
    lambda q: bool(re.search(r"(比较|对比|区别|不同)", q)),           # 比较
    lambda q: bool(re.search(r"(以及|并且|同时|还有).+\?", q)),      # 多个并列要求
    lambda q: len(q) > 80,                            # 长查询
]


def classify_query(query: str) -> QueryComplexity:
    """
    分类查询复杂度。

    Args:
        query: 用户查询

    Returns:
        QueryComplexity 枚举值
    """
    # 先检查是否复杂
    complex_score = sum(1 for fn in COMPLEX_INDICATORS if fn(query))
    if complex_score >= 2:
        logger.info(f"[QueryRouter] COMPLEX query: {query[:30]}...")
        return QueryComplexity.COMPLEX

    # 再检查是否简单
    simple_score = sum(1 for fn in SIMPLE_INDICATORS if fn(query))
    if simple_score >= 1:
        logger.info(f"[QueryRouter] SIMPLE query: {query[:30]}...")
        return QueryComplexity.SIMPLE

    logger.info(f"[QueryRouter] STANDARD query: {query[:30]}...")
    return QueryComplexity.STANDARD


def decompose_query(query: str) -> list[str]:
    """
    将复杂查询分解为多个子查询（基于规则）。
    返回子查询列表，至少包含原始查询。
    """
    sub_queries = [query]

    # 按中文问号拆分
    if "？" in query:
        parts = [p.strip() for p in query.split("？") if p.strip()]
        if len(parts) > 1:
            sub_queries = [p + "？" if not p.endswith("？") else p for p in parts]

    # 按 "以及"/"并且"/"同时" 拆分
    elif re.search(r"(以及|并且|同时|还有)", query):
        parts = re.split(r"(?:以及|并且|同时|还有)", query)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
        if len(parts) > 1:
            sub_queries = parts

    logger.info(f"[QueryRouter] Decomposed into {len(sub_queries)} sub-queries")
    return sub_queries
