import uuid
import logging
from pathlib import Path
from typing import List, Optional

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.config import settings
from app.services.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manages per-session persistent ChromaDB collections.
    Each uploaded document gets its own collection keyed by session_id.
    """

    def __init__(self) -> None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        logger.info("ChromaDB persistent client initialised at %s", persist_dir)

    # ── public API ──────────────────────────────────────────────────────────

    def create_session(self, chunks: List[Document]) -> str:
        """Embed chunks and store them in a new collection. Returns session_id."""
        session_id = uuid.uuid4().hex
        collection_name = f"session_{session_id}"

        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=get_embeddings(),
            client=self._client,
            collection_name=collection_name,
        )
        logger.info(
            "Created collection %s with %d chunks", collection_name, len(chunks)
        )
        return session_id

    def get_retriever(self, session_id: str, top_k: int = 5):
        """Return a LangChain retriever for an existing session."""
        collection_name = f"session_{session_id}"
        self._assert_collection_exists(collection_name)

        vector_store = Chroma(
            client=self._client,
            collection_name=collection_name,
            embedding_function=get_embeddings(),
        )
        return vector_store.as_retriever(search_kwargs={"k": top_k})

    def similarity_search(
        self, session_id: str, query: str, top_k: int = 5
    ) -> List[Document]:
        """Direct similarity search, returns Document list."""
        collection_name = f"session_{session_id}"
        self._assert_collection_exists(collection_name)

        vector_store = Chroma(
            client=self._client,
            collection_name=collection_name,
            embedding_function=get_embeddings(),
        )
        return vector_store.similarity_search(query, k=top_k)

    def session_exists(self, session_id: str) -> bool:
        try:
            self._client.get_collection(f"session_{session_id}")
            return True
        except Exception:
            return False

    def delete_session(self, session_id: str) -> None:
        collection_name = f"session_{session_id}"
        try:
            self._client.delete_collection(collection_name)
            logger.info("Deleted collection %s", collection_name)
        except Exception as exc:
            logger.warning("Could not delete collection %s: %s", collection_name, exc)

    def list_sessions(self) -> List[str]:
        collections = self._client.list_collections()
        sessions = []
        for col in collections:
            name = col.name if hasattr(col, "name") else str(col)
            if name.startswith("session_"):
                sessions.append(name[len("session_"):])
        return sessions

    # ── private helpers ─────────────────────────────────────────────────────

    def _assert_collection_exists(self, collection_name: str) -> None:
        try:
            self._client.get_collection(collection_name)
        except Exception:
            raise ValueError(
                f"Session not found. Please upload a document first."
            )


# Module-level singleton — created once, reused across requests
_manager: Optional[VectorStoreManager] = None


def get_vector_store_manager() -> VectorStoreManager:
    global _manager
    if _manager is None:
        _manager = VectorStoreManager()
    return _manager
