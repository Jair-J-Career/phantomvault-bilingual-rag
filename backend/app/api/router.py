from fastapi import APIRouter
from app.api.endpoints import upload, ask, health, agent

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(upload.router, prefix="/api", tags=["documents"])
api_router.include_router(ask.router, prefix="/api", tags=["rag"])
api_router.include_router(agent.router, prefix="/api", tags=["agent"])
