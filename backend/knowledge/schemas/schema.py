from typing import List, Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    message: str
    file_name: str
    chunks_added: int
    document_id: Optional[str] = None
    duplicate: bool = False


class Citation(BaseModel):
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    source_filename: Optional[str] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation] = []


class QueryRequest(BaseModel):
    question: str


class RetrievalResponse(BaseModel):
    question: str
    contexts: List[str]


class DocumentListResponse(BaseModel):
    total: int
    documents: List[dict]


class DocumentActionResponse(BaseModel):
    success: bool
    document_id: str
    message: str
