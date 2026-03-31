"""
POST /api/agent — Agentic RAG endpoint.
Supports synchronous (stream=false) and SSE streaming (stream=true) modes.
"""
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import PlannerAgent
from app.limiter import limiter
from app.models.schemas import AgentRequest, AgentResponse, ErrorResponse, StepResult
from app.services.vector_store import get_vector_store_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/agent",
    responses={
        200: {"description": "Agent response (sync) or SSE stream"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit("10/minute")
async def run_agent(request: Request, body: AgentRequest):
    manager = get_vector_store_manager()
    if not manager.session_exists(body.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload a document first.",
        )

    agent = PlannerAgent(session_id=body.session_id)

    if body.stream:
        return StreamingResponse(
            _sse_generator(agent, body.query),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Synchronous mode
    try:
        answer, steps = agent.run(body.query)
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Agent execution failed.")

    return AgentResponse(
        query=body.query,
        answer=answer,
        steps=steps,
        session_id=body.session_id,
    )


async def _sse_generator(agent: PlannerAgent, query: str):
    """Yields SSE events for each agent step, then the final answer event."""
    try:
        final_answer = ""
        steps = []
        for step_result in agent.stream(query):
            steps.append(step_result)
            if step_result.tool == "answer" or step_result.tool == "summarize":
                final_answer = step_result.output_summary

            event_data = json.dumps(
                {
                    "type": "step",
                    "tool": step_result.tool,
                    "input_summary": step_result.input_summary,
                    "output_summary": step_result.output_summary,
                    "latency_ms": step_result.latency_ms,
                    "status": step_result.status,
                }
            )
            yield f"data: {event_data}\n\n"

        # Final answer event
        done_data = json.dumps({"type": "done", "answer": final_answer})
        yield f"data: {done_data}\n\n"

    except Exception as exc:
        logger.error("SSE stream error: %s", exc, exc_info=True)
        error_data = json.dumps({"type": "error", "message": str(exc)})
        yield f"data: {error_data}\n\n"
