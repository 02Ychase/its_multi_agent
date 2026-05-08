"""

创建FastAPI实例 并且管理所有的路由

"""
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库表
    try:
        from repositories.document_repository import init_document_tables
        from repositories.evaluation_repository import init_evaluation_tables
        init_document_tables()
        init_evaluation_tables()
        logger.info("知识库文档表和评测表初始化完成")
    except Exception as e:
        logger.error(f"知识库表初始化失败: {str(e)}")

    yield


def create_fast_api()->FastAPI:
    # 1. 创建FastApi实例
    app=FastAPI(title="Knowledge API", lifespan=lifespan)

    # 2. 注册各种路由
    app.include_router(router=router)

    # 3.返回创建的FastAPI
    return app


if __name__ == '__main__':
    print("1.准备启动Web服务器")
    try:
        uvicorn.run(app=create_fast_api(),host="127.0.0.1",port=8001)
        logger.info("2.启动Web服务器成功...")
    except KeyboardInterrupt as e:
        logger.error(f"2.启动Web服务器失败: {str(e)}")
