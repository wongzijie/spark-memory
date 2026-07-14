from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> dict[str, str]:
    async with request.app.state.sessionmaker() as session:
        await session.execute(text("SELECT 1"))
    await request.app.state.redis.ping()
    return {"status": "ready"}
