from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.db import get_async_db
from app.services.ai.agent import agent

router = APIRouter(tags=["healthcheck"])


@router.get("/healthcheck")
async def healthcheck() -> dict:
    """Liveness probe: returns 200 OK if the app can serve requests."""
    return {"status": "ok"}


@router.get("/readiness")
async def readiness(db: AsyncSession = Depends(get_async_db)) -> dict:
    """Readiness probe: verifies DB connectivity (async)."""
    await db.scalar(select(1))
    return {"status": "ready"}


@router.get("/agent-health")
async def agent_health() -> dict:
    """Check if the AI agent is available and functioning."""
    if agent is None:
        return {"status": "unavailable", "agent_available": False}
    
    return {"status": "healthy", "agent_available": True}
