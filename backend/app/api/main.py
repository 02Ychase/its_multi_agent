from contextlib import asynccontextmanager

import uvicorn
from api.auth_router import router as auth_router
from api.routers import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.logging.logger import logger
from infrastructure.observability.langfuse_client import flush_langfuse
from infrastructure.rate_limiter import limiter
from infrastructure.tools.mcp.mcp_manager import mcp_cleanup, mcp_connect
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理

    在应用启动时建立MCP连接，在应用关闭时清理连接。
    确保资源正确初始化和释放。
    """
    # 应用启动时执行
    logger.info("应用启动，建立MCP连接...")
    try:
        await mcp_connect()
        logger.info("MCP连接建立完成")
    except Exception as e:
        logger.error(f"MCP连接建立失败: {str(e)}")

    try:
        from models.user import init_users_table
        init_users_table()
        logger.info("用户表初始化完成")
    except Exception as e:
        logger.error(f"用户表初始化失败: {str(e)}")

    try:
        from repositories.agent_event_repository import init_agent_event_tables
        from repositories.chat_message_repository import init_chat_messages_table
        from repositories.chat_session_repository import init_chat_sessions_table
        init_chat_sessions_table()
        init_chat_messages_table()
        init_agent_event_tables()
        logger.info("会话相关表初始化完成")
    except Exception as e:
        logger.error(f"会话相关表初始化失败: {str(e)}")

    try:
        from models.refresh_token import init_refresh_tokens_table
        init_refresh_tokens_table()
        logger.info("refresh_tokens表初始化完成")
    except Exception as e:
        logger.error(f"refresh_tokens表初始化失败: {str(e)}")

    try:
        from repositories.tool_call_repository import init_tool_call_logs_table
        init_tool_call_logs_table()
        logger.info("tool_call_logs表初始化完成")
    except Exception as e:
        logger.error(f"tool_call_logs表初始化失败: {str(e)}")

    try:
        from repositories.after_sales_repository import init_after_sales_tables
        init_after_sales_tables()
        logger.info("售后相关表初始化完成")
    except Exception as e:
        logger.error(f"售后相关表初始化失败: {str(e)}")

    try:
        from repositories.feedback_repository import init_feedback_table
        init_feedback_table()
        logger.info("feedback表初始化完成")
    except Exception as e:
        logger.error(f"feedback表初始化失败: {str(e)}")

    yield  # 应用运行期间（先别释放mcp链接 去处理请求...）

    # 应用关闭时执行
    logger.info("应用关闭，清理MCP连接...")
    try:
        await mcp_cleanup()
        logger.info("MCP连接清理完成")
    except Exception as e:
        logger.error(f"MCP连接清理失败: {str(e)}")

    flush_langfuse()
    logger.info("Langfuse事件已刷新")


def create_fast_api() -> FastAPI:
    # 1. 创建FastApi实例,绑定了生命周期事件
    app = FastAPI(title="ITS API", lifespan=lifespan)

    # 注册限流器
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 2. 处理跨域 - 使用可配置的来源
    from config.settings import settings
    origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. 注册各种路由
    app.include_router(router=router)
    app.include_router(router=auth_router)

    # 4.返回创建的FastAPI
    return app


if __name__ == '__main__':
    print("1.准备启动Web服务器")
    try:
        uvicorn.run(app=create_fast_api(), host="127.0.0.1", port=8000)

        logger.info("2.启动Web服务器成功...")

    except KeyboardInterrupt as e:
        logger.error(f"2.启动Web服务器失败: {str(e)}")
