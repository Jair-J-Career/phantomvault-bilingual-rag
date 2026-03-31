"""
Background cleanup: deletes uploaded files and ChromaDB collections
that are older than MAX_AGE_HOURS hours.
Called from the FastAPI lifespan on startup and can be triggered manually.
"""
import logging
import os
import time
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

MAX_AGE_HOURS = 24
MAX_AGE_SECONDS = MAX_AGE_HOURS * 3600


def cleanup_old_uploads() -> int:
    """Delete uploaded PDF files older than MAX_AGE_HOURS. Returns count deleted."""
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return 0

    cutoff = time.time() - MAX_AGE_SECONDS
    deleted = 0
    for f in upload_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                logger.info("Cleanup: deleted upload %s", f.name)
                deleted += 1
            except OSError as exc:
                logger.warning("Cleanup: could not delete %s: %s", f.name, exc)
    return deleted


def cleanup_old_collections() -> int:
    """Delete ChromaDB collections whose backing metadata is older than MAX_AGE_HOURS."""
    try:
        from app.services.vector_store import get_vector_store_manager
        import chromadb

        manager = get_vector_store_manager()
        chroma_dir = Path(settings.chroma_persist_dir)
        cutoff = time.time() - MAX_AGE_SECONDS
        deleted = 0

        for session_id in manager.list_sessions():
            # Proxy age via the chroma directory mtime of the collection folder
            col_path = chroma_dir / f"session_{session_id}"
            if col_path.exists() and col_path.stat().st_mtime < cutoff:
                manager.delete_session(session_id)
                logger.info("Cleanup: deleted collection for session %s", session_id)
                deleted += 1

        return deleted
    except Exception as exc:
        logger.warning("Collection cleanup failed: %s", exc)
        return 0


def run_cleanup() -> dict:
    uploads = cleanup_old_uploads()
    collections = cleanup_old_collections()
    logger.info("Cleanup complete: %d uploads, %d collections removed", uploads, collections)
    return {"uploads_deleted": uploads, "collections_deleted": collections}
