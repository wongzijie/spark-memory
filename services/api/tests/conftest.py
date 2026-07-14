import asyncio
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import create_engine_and_sessionmaker
from app.main import create_app
from app.models import Base, RawCapture, User


def pytest_asyncio_loop_factories(config, item):
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    return {"spark-memory": factory}


@pytest.fixture
def valid_settings_data() -> dict[str, object]:
    return {
        "database_url": "postgresql+psycopg://spark:spark-local-only@127.0.0.1:5432/spark_test",
        "redis_url": "redis://127.0.0.1:6379/1",
        "llm_api_key": "test-llm-token-that-is-not-real-0000000001",
        "llm_base_url": "https://llm.example.invalid/v1",
        "llm_model": "mimo-v2.5-pro",
        "tavily_api_key": "test-tavily-token-that-is-not-real-0001",
        "tavily_base_url": "https://api.tavily.com",
        "telegram_bot_token": "test-bot-token-that-is-not-real-0000000001",
        "telegram_bot_id": "test-bot",
        "telegram_allowed_user_id": 7788,
        "telegram_webhook_path_secret": "test-path-secret-that-is-not-real-0001",
        "telegram_webhook_header_secret": "test-header-secret-that-is-not-real-01",
        "public_base_url": "https://example.invalid",
    }


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch, valid_settings_data):
    for name, value in valid_settings_data.items():
        monkeypatch.setenv(f"SPARK_{name.upper()}", str(value))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncClient:
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client


@pytest.fixture
async def db_session() -> AsyncSession:
    engine, session_factory = create_engine_and_sessionmaker(get_settings())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await engine.dispose()


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    record = User(email="owner@example.com", password_hash="not-used-in-this-test")
    db_session.add(record)
    await db_session.flush()
    return record


@pytest.fixture
async def raw_capture(db_session: AsyncSession, user: User) -> RawCapture:
    record = RawCapture(
        user_id=user.id,
        telegram_bot_id="bot-1",
        telegram_update_id=1,
        telegram_message_id=2,
        telegram_chat_id=3,
        telegram_user_id=4,
        raw_update={"update_id": 1},
        original_text="原始内容  不修改",
    )
    db_session.add(record)
    await db_session.flush()
    return record
