from unittest.mock import MagicMock

from services.citation_service import build_citations


def test_build_citations_from_documents():
    doc = MagicMock()
    doc.metadata = {
        "document_id": "doc123",
        "chunk_id": "doc123:chunk:0",
        "title": "Windows 蓝屏处理",
        "source_filename": "kb_blue_screen.md",
        "chunk_index": 0,
        "reranker_score": 0.91,
    }
    citations = build_citations([doc])
    assert len(citations) == 1
    assert citations[0]["document_id"] == "doc123"
    assert citations[0]["title"] == "Windows 蓝屏处理"


def test_build_citations_deduplicates_same_chunk_id():
    doc1 = MagicMock()
    doc1.metadata = {"chunk_id": "doc123:chunk:0", "title": "Title A"}
    doc2 = MagicMock()
    doc2.metadata = {"chunk_id": "doc123:chunk:0", "title": "Title A"}
    citations = build_citations([doc1, doc2])
    assert len(citations) == 1


def test_build_citations_returns_empty_for_no_metadata():
    doc = MagicMock()
    doc.metadata = {}
    citations = build_citations([doc])
    assert len(citations) == 1
    assert citations[0]["document_id"] is None


def test_build_citations_includes_score():
    doc = MagicMock()
    doc.metadata = {
        "chunk_id": "doc1:chunk:0",
        "title": "Test",
        "similarity": 0.85,
    }
    citations = build_citations([doc])
    assert citations[0]["score"] == 0.85
