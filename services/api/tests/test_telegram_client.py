import json
import logging

import httpx
import pytest

from app.telegram.client import TelegramClient, TelegramClientError

TOKEN = "test-bot-token-that-is-not-real-0000000001"


async def test_set_webhook_sends_expected_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "result": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TelegramClient(TOKEN, http_client=http_client)
        result = await client.set_webhook(
            public_base_url="https://spark.example",
            path_secret="path-secret-000000000000000000000001",
            header_secret="header-secret-0000000000000000000001",
        )

    assert result is True
    assert captured["url"].endswith(f"/bot{TOKEN}/setWebhook")
    assert captured["payload"] == {
        "url": ("https://spark.example/api/telegram/webhook/path-secret-000000000000000000000001"),
        "secret_token": "header-secret-0000000000000000000001",
        "allowed_updates": ["message"],
    }


async def test_telegram_error_never_exposes_token(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"ok": False, "description": "unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TelegramClient(TOKEN, http_client=http_client)
        with caplog.at_level(logging.ERROR), pytest.raises(TelegramClientError) as exc_info:
            await client.get_me()

    assert TOKEN not in str(exc_info.value)
    assert TOKEN not in caplog.text
