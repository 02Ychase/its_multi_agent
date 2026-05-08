from fastapi.routing import APIRouter
from fastapi import Depends
from starlette.responses import StreamingResponse

from schemas.request import ChatMessageRequest, UserSessionsRequest, DeleteSessionRequest
from services.agent_service import MultiAgentService
from infrastructure.logging.logger import logger
from services.conversation_service import conversation_service
from repositories.tool_call_repository import get_tool_call_summary
from api.auth_router import get_current_user

# 1. 定义请求路由器
router = APIRouter()


# 2. 定义对话请求
@router.post("/api/query", summary="智能体对话接口")
async def query(request_context: ChatMessageRequest, current_user: dict = Depends(get_current_user)) -> StreamingResponse:
    """
    SSE返回数据（流式响应）
    响应头中：text/event-stream
    """

    # 1. 获取请求上下文的属性
    user_id = current_user["user_id"]
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
