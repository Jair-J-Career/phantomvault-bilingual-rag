import os
from fastapi import APIRouter
from app.models.schemas import HealthResponse, HealthStatus
from app.services.vector_store import get_vector_store_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    api_key_present = bool(os.environ.get("GOOGLE_API_KEY"))

    try:
        mgr = get_vector_store_manager()
        mgr.list_sessions()  # lightweight probe
        chroma_status = "ok"
    except Exception as exc:
        chroma_status = f"error: {exc}"

    overall = (
        HealthStatus.ok
        if chroma_status == "ok" and api_key_present
        else HealthStatus.degraded
    )

    return HealthResponse(
        status=overall,
        chroma=chroma_status,
        google_api_key_present=api_key_present,
    )


@router.get("/ready")
def readiness():
    """Simple readiness probe — returns 200 if the service can accept traffic."""
    return {"ready": True}
