import logging

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RerankerService:
    """
    Reranking service using BAAI/bge-reranker-v2-m3.
    Replaces cosine similarity reranking with a cross-encoder model.
    """

    def __init__(self):
        self.reranker = None
        self._load_model()

    def _load_model(self):
        """Lazy load the reranker model."""
        try:
            from FlagEmbedding import FlagReranker
            self.reranker = FlagReranker(
                settings.RERANKER_MODEL,
                use_fp16=True
            )
            logger.info(f"Reranker model loaded: {settings.RERANKER_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.reranker = None

    def rerank(self, query: str, documents: list, top_k: int = None) -> list:
        """
        Rerank documents based on relevance to query.

        Args:
            query: The user's question
            documents: List of Document objects to rerank
            top_k: Number of top results to return (default: settings.TOP_FINAL)

        Returns:
            List of Document objects sorted by reranker score (descending)
        """
        if top_k is None:
            top_k = settings.TOP_FINAL

        if not documents:
            return []

        if self.reranker is None:
            logger.warning("Reranker not available, returning documents as-is")
            return documents[:top_k]

        try:
            # Prepare query-document pairs for scoring
            pairs = [[query, doc.page_content] for doc in documents]

            # Compute reranker scores
            scores = self.reranker.compute_score(pairs)

            # Handle single score vs list of scores
            if isinstance(scores, (int, float)):
                scores = [scores]

            # Sort by score descending
            scored_docs = sorted(
                zip(documents, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # Update metadata with reranker scores and return top-k
            result = []
            for doc, score in scored_docs[:top_k]:
                doc.metadata['reranker_score'] = float(score)
                result.append(doc)

            logger.info(f"Reranker returned {len(result)} documents, top score: {scores[0]:.4f}")
            return result

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:top_k]


reranker_service = RerankerService()
