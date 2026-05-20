import logging
from typing import List, Dict, Any

from app.services.vector_store import get_vector_store_manager

logger = logging.getLogger(__name__)


def retrieve_chunks(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    manager = get_vector_store_manager()
    docs = manager.similarity_search(session_id, query, top_k=top_k)

    results = [
        {
            "content": doc.page_content,
            "page": doc.metadata.get("page", "?"),
            "source": doc.metadata.get("source", "unknown"),
        }
        for doc in docs
    ]
    logger.info("Retrieved %d chunks for query: %r", len(results), query[:60])
    return results
