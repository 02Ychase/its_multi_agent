
from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    message: str
    file_name: str
    chunks_added: int
    document_id: str | None = None
    duplicate: bool = False


class Citation(BaseModel):
    document_id: str | None = None
    chunk_id: str | None = None
    title: str | None = None
    source_filename: str | None = None
    chunk_index: int | None = None
    score: float | None = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = []


class QueryRequest(BaseModel):
    question: str


class RetrievalResponse(BaseModel):
    question: str
    contexts: list[str]


class DocumentListResponse(BaseModel):
    total: int
    documents: list[dict]


class DocumentActionResponse(BaseModel):
    success: bool
    document_id: str
    message: str
