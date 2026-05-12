import logging
import os.path
import shutil

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from config.settings import settings
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from schemas.schema import (
    DocumentActionResponse,
    DocumentListResponse,
    QueryRequest,
    QueryResponse,
    RetrievalResponse,
    UploadResponse,
)
from services import document_service
from services.citation_service import build_citations
from services.ingestion.ingestion_processor import IngestionProcessor
from services.query_service import QueryService
from services.retrieval_service import RetrievalService
from services.upload_validation import sanitize_filename, validate_upload_extension, validate_upload_size

# 1.创建APIRouter
router = APIRouter()
# 2. 创建应用的实例
ingestion_processor = IngestionProcessor()
retrieval_service = RetrievalService()
query_service = QueryService()


# IO(对文件读写) 执行SQL 网络请求 典型耗时任务
@router.post("/upload", response_model=UploadResponse, summary="处理知识库上传")
async def upload_file(file: UploadFile = File(...)):
    temp_file_path = None
    tmp_md_path = None

    try:
        # 0. 文件名清理和格式校验
        safe_filename = sanitize_filename(file.filename)
        file_suffix = validate_upload_extension(safe_filename)
        file_content = await file.read()
        validate_upload_size(len(file_content))

        # 0.1 临时目录
        temp_md_dir = settings.TMP_MD_FOLDER_PATH
        os.makedirs(temp_md_dir, exist_ok=True)
        tmp_md_path = os.path.join(temp_md_dir, safe_filename)

        # 1. 写入临时文件
        with open(tmp_md_path, "wb") as f:
            f.write(file_content)
        temp_file_path = tmp_md_path

        # 2. 计算文件哈希，检查重复
        file_hash = document_service.sha256_file(tmp_md_path)
        existing_doc = document_service.check_duplicate(file_hash)
        if existing_doc:
            logger.info(f"文档已存在，跳过重复入库: {existing_doc['document_id']}")
            return UploadResponse(
                status="success",
                message="文档已存在，跳过重复入库",
                file_name=file.filename,
                chunks_added=0,
                document_id=existing_doc["document_id"],
                duplicate=True,
            )

        # 3. 创建文档记录
        doc_record = document_service.create_document_record(
            filename=safe_filename,
            original_filename=file.filename,
            file_hash=file_hash,
            file_ext=file_suffix,
            storage_path=tmp_md_path,
        )
        document_id = doc_record["document_id"]

        # 4. 更新状态：解析中
        document_service.update_document_status(document_id, "parsing")

        # 5. 执行解析和入库
        try:
            chunks_added = await run_in_threadpool(ingestion_processor.ingest_file, tmp_md_path)
        except Exception as e:
            document_service.update_document_status(document_id, "failed", error_message=str(e))
            raise

        # 6. 更新状态：已索引
        document_service.update_document_status(document_id, "indexed", chunk_count=chunks_added)

        # 7. 保存到永久目录
        uploaded_dir = os.path.join(settings._project_root, "data", "uploaded")
        os.makedirs(uploaded_dir, exist_ok=True)
        permanent_path = os.path.join(uploaded_dir, safe_filename)
        shutil.copy2(tmp_md_path, permanent_path)
        logger.info(f"文档已保存到永久目录:{permanent_path}")

        # 8. 触发 BM25 索引重建
        try:
            retrieval_service.bm25_retriever.rebuild_index()
        except Exception as e:
            logger.warning(f"BM25 索引重建失败（不影响上传）: {e}")

        return UploadResponse(
            status="success",
            message="文档上传知识库成功",
            file_name=file.filename,
            chunks_added=chunks_added,
            document_id=document_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传到知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传到知识库失败:{str(e)}")

    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"临时文件:{temp_file_path}已删除...")
            except Exception:
                pass


@router.post("/query", response_model=QueryResponse, summary="查询知识库")
async def query(request: QueryRequest):
    """
    查询知识库，返回答案和引用来源。
    """
    try:
        user_question = request.question
        if not user_question:
            raise HTTPException(status_code=500, detail="查询问题不存在")

        # 1. 检索
        retrieval_context = retrieval_service.retrieval(user_question)

        # 2. 生成答案
        answer = query_service.generate_answer(user_question, retrieval_context)

        # 3. 构建引用来源
        citations = build_citations(retrieval_context)

        return QueryResponse(
            question=user_question,
            answer=answer,
            citations=citations,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调用查询知识库服务失败:原因:{str(e)}")
        raise HTTPException(status_code=500, detail="服务内部出现异常")


@router.post("/retrieval", response_model=RetrievalResponse, summary="检索知识库（返回原始上下文）")
async def retrieval(request: QueryRequest):
    """
    检索知识库，返回原始检索上下文（用于评测）。
    """
    try:
        user_question = request.question
        if not user_question:
            raise HTTPException(status_code=500, detail="查询问题不存在")

        retrieval_context = retrieval_service.retrieval(user_question)
        contexts = [doc.page_content for doc in retrieval_context]

        return RetrievalResponse(
            question=user_question,
            contexts=contexts
        )
    except Exception as e:
        logger.error(f"检索知识库失败:原因:{str(e)}")
        raise HTTPException(status_code=500, detail="服务内部出现异常")


@router.get("/documents", response_model=DocumentListResponse, summary="获取文档列表")
async def list_documents(status: str = None, limit: int = 50, offset: int = 0):
    """获取知识库文档列表，支持分页和状态过滤。"""
    try:
        total, docs = document_service.list_documents(status, limit, offset)
        formatted_docs = []
        for row in docs:
            formatted_docs.append({
                "id": row[0],
                "document_id": row[1],
                "filename": row[2],
                "original_filename": row[3],
                "status": row[4],
                "chunk_count": row[5],
                "created_at": row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else "",
            })
        return DocumentListResponse(total=total, documents=formatted_docs)
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文档列表失败")


@router.delete("/documents/{document_id}", response_model=DocumentActionResponse, summary="删除文档")
async def delete_document(document_id: str):
    """删除指定文档及其向量数据。"""
    try:
        doc = document_service.get_document(document_id)
        if not doc:
            return DocumentActionResponse(success=False, document_id=document_id, message="文档不存在")

        # 删除向量数据
        try:
            chunk_ids = document_service.get_chunk_vector_ids(doc["id"])
            if chunk_ids:
                from repositories.vector_store_repository import VectorStoreRepository
                vs = VectorStoreRepository()
                vs.vector_database.delete(ids=chunk_ids)
        except Exception as e:
            logger.warning(f"删除向量数据时出错: {e}")

        # 标记文档为已删除
        success = document_service.delete_document(document_id)
        if success:
            return DocumentActionResponse(success=True, document_id=document_id, message="文档已删除")
        else:
            return DocumentActionResponse(success=False, document_id=document_id, message="删除失败")
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文档失败")


@router.post("/documents/{document_id}/reindex", response_model=DocumentActionResponse, summary="重建文档索引")
async def reindex_document(document_id: str):
    """重新解析和索引指定文档。"""
    try:
        doc = document_service.get_document(document_id)
        if not doc:
            return DocumentActionResponse(success=False, document_id=document_id, message="文档不存在")

        storage_path = doc.get("storage_path")
        if not storage_path or not os.path.exists(storage_path):
            return DocumentActionResponse(success=False, document_id=document_id, message="文档源文件不存在")

        # 删除旧的向量数据
        try:
            chunk_ids = document_service.get_chunk_vector_ids(doc["id"])
            if chunk_ids:
                from repositories.vector_store_repository import VectorStoreRepository
                vs = VectorStoreRepository()
                vs.vector_database.delete(ids=chunk_ids)
        except Exception as e:
            logger.warning(f"删除旧向量数据时出错: {e}")

        # 清除旧的分块记录
        document_service.rebuild_chunks(doc["id"])

        # 更新状态：重建中
        document_service.update_document_status(document_id, "reindexing")

        # 重新解析和入库
        try:
            chunks_added = await run_in_threadpool(ingestion_processor.ingest_file, storage_path)
            document_service.update_document_status(document_id, "indexed", chunk_count=chunks_added)
            return DocumentActionResponse(success=True, document_id=document_id, message=f"重建索引成功，共 {chunks_added} 个分块")
        except Exception as e:
            document_service.update_document_status(document_id, "failed", error_message=str(e))
            return DocumentActionResponse(success=False, document_id=document_id, message=f"重建索引失败: {str(e)}")
    except Exception as e:
        logger.error(f"重建文档索引失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重建文档索引失败")


@router.get("/health", summary="知识库健康检查")
async def health_check():
    checks = {}
    try:
        from repositories.vector_store_repository import VectorStoreRepository
        vs = VectorStoreRepository()
        count = vs.vector_database._collection.count()
        checks["chromadb"] = f"ok ({count} vectors)"
    except Exception as e:
        checks["chromadb"] = f"error: {str(e)}"

    all_ok = all("ok" in v for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
