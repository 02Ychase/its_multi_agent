import logging

logger = logging.getLogger(__name__)


def build_citations(documents: list) -> list:
    citations = []
    seen = set()
    for doc in documents:
        metadata = doc.metadata if hasattr(doc, 'metadata') else (doc.get("metadata", {}) if isinstance(doc, dict) else {})
        key = metadata.get("chunk_id") or (metadata.get("title"), metadata.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "document_id": metadata.get("document_id"),
            "chunk_id": metadata.get("chunk_id"),
            "title": metadata.get("title"),
            "source_filename": metadata.get("source_filename") or metadata.get("path"),
            "chunk_index": metadata.get("chunk_index"),
            "score": metadata.get("reranker_score") or metadata.get("similarity") or metadata.get("bm25_score"),
        })
    return citations
