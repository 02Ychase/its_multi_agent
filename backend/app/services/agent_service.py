import re
from collections.abc import AsyncGenerator
from agents.run import Runner
from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from langfuse import observe
from multi_agent.orchestrator_agent import orchestrator_agent
from schemas.request import ChatMessageRequest
from services.session_service import session_service
from services.conversation_service import conversation_service
from services.stream_response_service import process_stream_response
from utils.response_util import ResponseFactory
from infrastructure.logging.logger import logger
import traceback
from schemas.response import ContentKind


class MultiAgentService:
    """
    多智能体业务服务类
    """

    @classmethod
    @observe(as_type="agent", name="orchestrator")
    async def process_task(cls, request: ChatMessageRequest, flag: bool, current_user: dict = None) -> AsyncGenerator:
        """
        多智能体处理任务入口
        Args:
            request:  请求上下文
            flag:  是否允许重试
            current_user: 当前认证用户信息 {"user_id": int, "username": str}

        Returns:
            AsyncGenerator：异步生成器对象
        """
        try:
            # 1. 获取请求上下文的信息
            user_id = request.context.user_id
            session_id = request.context.session_id
            user_query = request.query

            # 2. 准备历史对话 - 优先使用 token 身份
            if current_user:
                numeric_id = current_user["user_id"]
                username = current_user["username"]
                chat_history = await conversation_service.prepare_history(numeric_id, username, session_id, user_query)
            else:
                # 兼容旧调用方式
                chat_history = session_service.prepare_history(user_id, session_id, user_query)

            # 3. 运行Agent (流式模式，传入完整历史对话)
            streaming_result = Runner.run_streamed(
                starting_agent=orchestrator_agent,
                input=chat_history,
                max_turns=10,
            )

            # 4. 处理Agent的事件流（事件流）
            async for chunk in process_stream_response(streaming_result):
                yield chunk

            # 5. 获取Agent的结果
            agent_result = streaming_result.final_output

            format_agent_result = re.sub(r'\n+', '\n', agent_result)

            # 6. 存储历史对话 - 使用 ConversationService
            if current_user:
                conversation_service.save_assistant_final(
                    user_id=numeric_id,
                    username=username,
                    session_id=session_id,
                    content=format_agent_result,
                )
            else:
                chat_history.append({"role": "assistant", "content": format_agent_result})
                session_service.save_history(user_id, session_id, chat_history)

        except InputGuardrailTripwireTriggered as e:
            logger.warning(f"输入护栏触发: {e.guardrail_result.output_info}")
            reason = e.guardrail_result.output_info.get("reason", "unknown")
            if reason == "prompt_injection":
                msg = "检测到不安全的输入内容，请重新描述您的问题。"
            elif reason == "input_too_long":
                msg = "输入内容过长，请精简后重试（最多2000字）。"
            elif reason == "sensitive_content":
                msg = "请勿在对话中发送敏感个人信息。"
            else:
                msg = "输入内容不符合安全要求，请重新描述。"
            yield "data: " + ResponseFactory.build_text(
                msg, ContentKind.ANSWER
            ).model_dump_json() + "\n\n"
            yield "data: " + ResponseFactory.build_finish().model_dump_json() + "\n\n"

        except OutputGuardrailTripwireTriggered as e:
            logger.warning(f"输出护栏触发: {e.guardrail_result.output_info}")
            msg = "系统检测到回复内容可能包含敏感信息，已自动过滤。请重新提问。"
            yield "data: " + ResponseFactory.build_text(
                msg, ContentKind.ANSWER
            ).model_dump_json() + "\n\n"
            yield "data: " + ResponseFactory.build_finish().model_dump_json() + "\n\n"

        except Exception as e:
            # 记录错误日志
            logger.error(f"AgentService.process_query执行出错: {str(e)}")
            logger.debug(f"异常详情: {traceback.format_exc()}")

            text = f"❌ 系统错误: {str(e)}"
            yield "data: " + ResponseFactory.build_text(
                text, ContentKind.PROCESS
            ).model_dump_json() + "\n\n"

            # 如果允许重试，则启动重试流程
            if flag:
                text = f"🔄 正在尝试自动重试..."
                yield "data: " + ResponseFactory.build_text(
                    text, ContentKind.PROCESS
                ).model_dump_json() + "\n\n"

                # 递归调用进行重试
                async for item in MultiAgentService.process_task(request, flag=False, current_user=current_user):
                    yield item
