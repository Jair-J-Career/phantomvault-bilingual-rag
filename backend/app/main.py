import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.api.router import api_router

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    logger.info("PhantomVault API starting up")

    # Run startup cleanup to remove stale data from previous runs
    try:
        from app.services.cleanup import run_cleanup
        result = run_cleanup()
        logger.info("Startup cleanup: %s", result)
    except Exception as exc:
        logger.warning("Startup cleanup failed (non-fatal): %s", exc)

    yield
    logger.info("PhantomVault API shutting down")


# ── app factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="PhantomVault Bilingual RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter state and handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception [request_id=%s]: %s", request_id, exc, exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": request_id},
    )


# ── routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/")
def root():
    return {"status": "PhantomVault API is Online (Bilingual Mode)", "version": "1.0.0"}
