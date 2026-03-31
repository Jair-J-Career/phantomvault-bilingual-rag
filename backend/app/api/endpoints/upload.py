import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.config import settings
from app.models.schemas import ErrorResponse, UploadResponse
from app.services.document_processor import load_and_split
from app.services.vector_store import get_vector_store_manager

router = APIRouter()
logger = logging.getLogger(__name__)

from app.limiter import limiter
_rate_limit = limiter.limit("5/minute")

_PDF_MAGIC = b"%PDF"


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
)
@_rate_limit
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    # ── validation ───────────────────────────────────────────────────────────
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()

    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size // (1024*1024)} MB.",
        )

    if not content.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=400, detail="File does not appear to be a valid PDF."
        )

    # ── sanitise filename and persist ────────────────────────────────────────
    safe_name = Path(file.filename or "upload.pdf").name
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_name

    try:
        file_path.write_bytes(content)
        logger.info("Saved upload: %s (%d bytes)", safe_name, len(content))
    except OSError as exc:
        logger.error("Failed to write upload: %s", exc)
        raise HTTPException(status_code=500, detail="Could not save uploaded file.")

    # ── process and embed ────────────────────────────────────────────────────
    try:
        chunks = load_and_split(file_path)
        if not chunks:
            raise HTTPException(
                status_code=400, detail="The PDF appears to contain no extractable text."
            )
        manager = get_vector_store_manager()
        session_id = manager.create_session(chunks)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Processing failed for %s: %s", safe_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process PDF.")

    return UploadResponse(
        status="File processed and memorized!",
        session_id=session_id,
        chunks=len(chunks),
        filename=safe_name,
    )
