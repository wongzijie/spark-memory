from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.config import get_settings
from app.db import create_engine_and_sessionmaker
from app.health.router import router as health_router
from app.redis import create_redis
from app.telegram.router import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine, sessionmaker = create_engine_and_sessionmaker(settings)
    redis = create_redis(settings)
    app.state.settings = settings
    app.state.db_engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Spark Memory API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(telegram_router)
    return app


app = create_app()
