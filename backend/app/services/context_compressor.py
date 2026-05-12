"""
对话上下文压缩服务。
将超出滑动窗口的历史消息用 LLM 压缩为摘要。
"""

from typing import List, Dict, Any
from infrastructure.ai.openai_client import sub_model_client
from config.settings import settings
from infrastructure.logging.logger import logger


SUMMARY_PROMPT = """请用中文将以下对话历史压缩为一段简洁的摘要（不超过200字）。
重点保留：
1. 用户提到的设备型号、品牌
2. 用户遇到的具体问题和诉求
3. 系统已给出的关键建议或操作结果
4. 任何重要的上下文信息（如位置、订单号、工单号）

不要保留寒暄、重复内容或系统内部的工具调用细节。

对话历史：
{conversation}

摘要："""


async def compress_history(
    messages: List[Dict[str, Any]],
    keep_recent: int = 3,
) -> List[Dict[str, Any]]:
    """
    压缩对话历史：保留最近 keep_recent 轮 + 将更早的对话压缩为摘要。

    Args:
        messages: 完整对话历史（不含 system 消息）
        keep_recent: 保留的最近轮数（1轮=1对 user+assistant）

    Returns:
        压缩后的消息列表，格式为 [system_summary, ...recent_messages]
    """
    msg_limit = keep_recent * 2
    if len(messages) <= msg_limit:
        return messages

    # 分割：需要压缩的旧消息 vs 保留的近期消息
    old_messages = messages[:-msg_limit]
    recent_messages = messages[-msg_limit:]

    # 构建对话文本
    conversation_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:300]}"
        for m in old_messages
    )

    try:
        response = await sub_model_client.chat.completions.create(
            model=settings.SUB_MODEL_NAME,
            messages=[{"role": "user", "content": SUMMARY_PROMPT.format(conversation=conversation_text)}],
            temperature=0,
            max_tokens=300,
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"对话摘要生成成功: {len(summary)} 字符")
    except Exception as e:
        logger.warning(f"对话摘要生成失败，回退到简单截断: {e}")
        return recent_messages

    # 将摘要作为 system 消息注入
    summary_message = {
        "role": "system",
        "content": f"以下是之前对话的摘要，供你理解用户上下文：\n{summary}"
    }

    return [summary_message] + recent_messages
