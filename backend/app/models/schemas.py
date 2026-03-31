from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class UploadResponse(BaseModel):
    status: str
    session_id: str
    chunks: int
    filename: str


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    answer: str
    session_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthStatus(str, Enum):
    ok = "ok"
    degraded = "degraded"
    unavailable = "unavailable"


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "1.0.0"
    chroma: str
    google_api_key_present: bool


# ── Agentic RAG schemas ──────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    session_id: str
    query: str = Field(..., min_length=1, max_length=2000)
    stream: bool = False


class StepResult(BaseModel):
    tool: str
    input_summary: str
    output_summary: str
    latency_ms: int
    status: str = "completed"


class AgentResponse(BaseModel):
    query: str
    answer: str
    steps: List[StepResult]
    session_id: str
