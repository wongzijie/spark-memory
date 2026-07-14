import asyncio
import sys

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app


def pytest_asyncio_loop_factories(config, item):
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    return {"spark-memory": factory}


@pytest.fixture
def valid_settings_data() -> dict[str, object]:
    return {
        "database_url": "postgresql+psycopg://spark:spark-local-only@127.0.0.1:5432/spark",
        "redis_url": "redis://127.0.0.1:6379/0",
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
