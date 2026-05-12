"""
Agent Guardrails — 输入/输出安全护栏

使用 openai-agents SDK 的 GuardrailFunctionOutput / InputGuardrail / OutputGuardrail 实现。
"""

from agents import (
    GuardrailFunctionOutput,
    InputGuardrail,
    OutputGuardrail,
    RunContextWrapper,
    Agent,
    Runner,
    TResponseInputItem,
)
from infrastructure.logging.logger import logger
from infrastructure.ai.openai_client import sub_model
from pydantic import BaseModel
import re
from typing import List


# ============================================================
# 1. 输入护栏：Prompt 注入检测
# ============================================================

# 1.1 基于规则的快速检测
INJECTION_PATTERNS = [
    r"忽略.*(?:之前|以上|所有).*(?:指令|规则|提示)",
    r"ignore.*(?:previous|above|all).*(?:instructions?|rules?|prompts?)",
    r"你(?:现在|从现在)是.*(?:角色|模式)",
    r"system\s*(?:prompt|message)",
    r"(?:jailbreak|越狱|DAN|developer\s*mode)",
    r"(?:假装|pretend|act\s+as).*(?:你是|you\s+are)",
    r"(?:不要|不需要|don'?t).*(?:遵守|遵循|follow).*(?:规则|限制|rules?)",
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# 1.2 输入长度限制
MAX_INPUT_LENGTH = 2000

# 1.3 敏感词列表（示例，实际部署时应从配置或数据库加载）
SENSITIVE_KEYWORDS = [
    "身份证号", "银行卡", "密码", "信用卡",
    "社保号", "护照号",
]


async def input_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | List[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """
    输入护栏函数。检测：
    1. Prompt 注入攻击
    2. 超长输入
    3. 敏感词

    返回 GuardrailFunctionOutput(output_info=..., tripwire_triggered=True/False)
    tripwire_triggered=True 时 Agent 会拒绝处理此输入。
    """
    # 将输入标准化为字符串
    if isinstance(input, list):
        text_parts = []
        for item in input:
            if isinstance(item, dict) and "content" in item:
                text_parts.append(str(item["content"]))
            elif isinstance(item, str):
                text_parts.append(item)
        text = " ".join(text_parts)
    else:
        text = str(input)

    # 检查 1：输入长度
    if len(text) > MAX_INPUT_LENGTH:
        logger.warning(f"[Guardrail] 输入超长: {len(text)} 字符")
        return GuardrailFunctionOutput(
            output_info={"reason": "input_too_long", "length": len(text)},
            tripwire_triggered=True,
        )

    # 检查 2：Prompt 注入模式
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            logger.warning(f"[Guardrail] 检测到 Prompt 注入: {pattern.pattern}")
            return GuardrailFunctionOutput(
                output_info={"reason": "prompt_injection", "pattern": pattern.pattern},
                tripwire_triggered=True,
            )

    # 检查 3：敏感词
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text:
            logger.warning(f"[Guardrail] 检测到敏感词: {keyword}")
            return GuardrailFunctionOutput(
                output_info={"reason": "sensitive_content", "keyword": keyword},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info={"reason": "passed"},
        tripwire_triggered=False,
    )


# ============================================================
# 2. 输出护栏：幻觉检测 + 敏感信息泄漏
# ============================================================

# 2.1 不应出现在输出中的敏感信息模式
OUTPUT_SENSITIVE_PATTERNS = [
    r"\b\d{17}[\dXx]\b",                   # 身份证号
    r"\b\d{16,19}\b",                       # 银行卡号（16-19位纯数字）
    r"\b(?:API[_\s]?KEY|api[_\s]?key)\s*[:=]\s*\S+",  # API Key 泄漏
]
COMPILED_OUTPUT_PATTERNS = [re.compile(p) for p in OUTPUT_SENSITIVE_PATTERNS]


async def output_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """
    输出护栏函数。检测：
    1. 输出中的敏感信息模式（身份证号、银行卡号等）

    注意：幻觉检测（判断回答是否基于工具返回内容）需要 LLM 评估，
    成本较高，可以通过异步采样方式实现，不在此同步护栏中处理。
    """
    if not output:
        return GuardrailFunctionOutput(
            output_info={"reason": "empty_output"},
            tripwire_triggered=False,
        )

    # 检查敏感信息泄漏
    for pattern in COMPILED_OUTPUT_PATTERNS:
        if pattern.search(output):
            logger.warning(f"[Guardrail] 输出包含敏感信息模式: {pattern.pattern}")
            return GuardrailFunctionOutput(
                output_info={"reason": "sensitive_output", "pattern": pattern.pattern},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info={"reason": "passed"},
        tripwire_triggered=False,
    )


# ============================================================
# 3. 构建 Guardrail 对象（供 Agent 定义使用）
# ============================================================

input_guardrail = InputGuardrail(guardrail_function=input_guardrail_fn)
output_guardrail = OutputGuardrail(guardrail_function=output_guardrail_fn)
