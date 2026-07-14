from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr


class TelegramClientError(Exception):
    pass


class TelegramClient:
    def __init__(
        self,
        token: SecretStr | str,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token.get_secret_value() if isinstance(token, SecretStr) else token
        self._http_client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> Self:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()

    async def _request(self, method: str, payload: dict[str, Any]) -> Any:
        client = self._http_client
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            self._http_client = client
            self._owns_client = True
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, TypeError, ValueError):
            raise TelegramClientError("Telegram API request failed") from None
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise TelegramClientError("Telegram API request failed")
        return body.get("result")

    async def get_me(self) -> dict[str, Any]:
        result = await self._request("getMe", {})
        if not isinstance(result, dict):
            raise TelegramClientError("Telegram API response was invalid")
        return result

    async def set_webhook(
        self,
        *,
        public_base_url: str,
        path_secret: str,
        header_secret: str,
    ) -> bool:
        webhook_url = f"{public_base_url.rstrip('/')}/api/telegram/webhook/{path_secret}"
        result = await self._request(
            "setWebhook",
            {
                "url": webhook_url,
                "secret_token": header_secret,
                "allowed_updates": ["message"],
            },
        )
        return result is True

    async def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        result = await self._request("sendMessage", {"chat_id": chat_id, "text": text})
        if not isinstance(result, dict):
            raise TelegramClientError("Telegram API response was invalid")
        return result
