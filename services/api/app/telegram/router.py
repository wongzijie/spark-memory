import logging
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select

from app.captures.service import create_capture_from_update
from app.models import User
from app.telegram.client import TelegramClient
from app.telegram.schemas import TelegramUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])


def not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/webhook/{path_secret}")
async def telegram_webhook(path_secret: str, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(
        path_secret, settings.telegram_webhook_path_secret.get_secret_value()
    ) or not secrets.compare_digest(
        header_secret, settings.telegram_webhook_header_secret.get_secret_value()
    ):
        raise not_found()

    raw_payload = await request.json()
    if not isinstance(raw_payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    try:
        update = TelegramUpdate.model_validate(raw_payload)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from None

    message = update.message
    if (
        message is None
        or message.from_ is None
        or message.chat.type != "private"
        or message.from_.id != settings.telegram_allowed_user_id
    ):
        raise not_found()

    async with request.app.state.sessionmaker() as session:
        user = await session.scalar(select(User).order_by(User.created_at).limit(1))
        if user is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        capture, _, created = await create_capture_from_update(
            session,
            user_id=user.id,
            bot_id=settings.telegram_bot_id,
            update=update,
            raw_update=raw_payload,
        )
        await session.commit()

    if created:
        try:
            async with TelegramClient(settings.telegram_bot_token) as telegram:
                await telegram.send_message(message.chat.id, "Spark 已保存")
        except Exception as exc:
            logger.warning("Telegram acknowledgement failed: %s", type(exc).__name__)

    return {"ok": True, "created": created, "capture_id": str(capture.id)}
