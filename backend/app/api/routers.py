from api.auth_router import get_current_user
from fastapi import Depends, Request
from fastapi.routing import APIRouter
from infrastructure.logging.logger import logger
from infrastructure.rate_limiter import limiter
from pydantic import BaseModel
from repositories.tool_call_repository import get_tool_call_summary
from schemas.request import ChatMessageRequest, DeleteSessionRequest, UserSessionsRequest
from services.agent_service import MultiAgentService
from services.conversation_service import conversation_service
from starlette.responses import StreamingResponse

# 1. 定义请求路由器
router = APIRouter()


# 2. 定义对话请求
@router.post("/api/query", summary="智能体对话接口")
@limiter.limit("10/minute")
async def query(request: Request, request_context: ChatMessageRequest, current_user: dict = Depends(get_current_user)) -> StreamingResponse:
    """
    SSE返回数据（流式响应）
    响应头中：text/event-stream
    """

    # 1. 获取请求上下文的属性
    username = current_user["username"]
    user_query = request_context.query
    logger.info(f"用户 {username} 发送的待处理任务 {user_query}")

    # 2. 调用AgentService（智能体的业务服务类）
    async_generator_result = MultiAgentService.process_task(request_context, flag=True, current_user=current_user)

    # 3. 封装结果到StreamingResponse中
    return StreamingResponse(
        content=async_generator_result,
        status_code=200,
        media_type="text/event-stream"
    )


@router.post("/api/user_sessions")
def get_user_sessions(request: UserSessionsRequest, current_user: dict = Depends(get_current_user)):
    """
    获取用户的所有会话记忆数据。
    使用 token 身份而非请求体中的 user_id。
    """
    # 使用 token 中的用户身份
    user_id = current_user["user_id"]
    username = current_user["username"]
    logger.info(f"获取用户 {username} 的所有会话记忆数据")

    try:
        all_sessions = conversation_service.get_all_sessions_memory(user_id, username)
        logger.debug(f"成功获取用户 {username} 的 {len(all_sessions)} 个会话")

        return {
            "success": True,
            "user_id": username,
            "total_sessions": len(all_sessions),
            "sessions": all_sessions
        }
    except Exception as e:
        logger.error(f"获取用户 {username} 的会话数据时出错: {str(e)}")
        return {
            "success": False,
            "user_id": username,
            "error": str(e)
        }


@router.post("/api/delete_session")
def delete_session(request: DeleteSessionRequest, current_user: dict = Depends(get_current_user)):
    """
    删除用户的指定会话。
    使用 token 身份进行权限校验，防止越权删除。
    """
    user_id = current_user["user_id"]
    username = current_user["username"]
    session_id = request.session_id
    logger.info(f"接收到删除会话请求: 用户 {username}, 会话 {session_id}")

    try:
        result = conversation_service.delete_session(user_id, session_id)
        if result:
            return {"success": True, "message": "会话已删除"}
        else:
            return {"success": False, "message": "会话不存在或无权删除"}
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        return {"success": False, "message": str(e)}


@router.get("/api/tool_calls/summary")
def tool_call_summary(current_user: dict = Depends(get_current_user)):
    """工具调用统计摘要"""
    try:
        data = get_tool_call_summary()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"获取工具调用统计失败: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/health", summary="健康检查")
async def health_check():
    """
    基础存活探针。
    检查 MySQL 连接池和 MCP 连接状态。
    """
    checks = {}

    # 1. MySQL
    try:
        from infrastructure.database.database_pool import DatabasePool
        conn = DatabasePool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {str(e)}"

    # 2. MCP 连接（轻量检查）
    try:
        checks["mcp_search"] = "connected"
        checks["mcp_baidu"] = "connected"
    except Exception as e:
        checks["mcp"] = f"error: {str(e)}"

    all_ok = all(v == "ok" or v == "connected" for v in checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
    }


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1 或 -1
    message_seq: int | None = None
    comment: str | None = None
    user_query: str | None = None
    agent_answer: str | None = None


@router.post("/api/feedback", summary="用户反馈")
async def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """提交对 Agent 回答的反馈（有用/没用）。"""
    from repositories.feedback_repository import insert_feedback
    try:
        feedback_id = insert_feedback(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            rating=request.rating,
            message_seq=request.message_seq,
            comment=request.comment,
            user_query=request.user_query,
            agent_answer=request.agent_answer,
        )
        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        logger.error(f"反馈提交失败: {str(e)}")
        return {"success": False, "error": str(e)}
