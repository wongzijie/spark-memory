import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobKind, ProcessingJob, RawCapture
from app.telegram.schemas import TelegramUpdate


async def create_capture_from_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    bot_id: str,
    update: TelegramUpdate,
    raw_update: dict | None = None,
) -> tuple[RawCapture, ProcessingJob | None, bool]:
    message = update.message
    if message is None or message.from_ is None:
        raise ValueError("A Telegram message and sender are required")

    source_payload = raw_update or update.model_dump(by_alias=True, exclude_unset=True)
    statement = (
        insert(RawCapture)
        .values(
            user_id=user_id,
            telegram_bot_id=bot_id,
            telegram_update_id=update.update_id,
            telegram_message_id=message.message_id,
            telegram_chat_id=message.chat.id,
            telegram_user_id=message.from_.id,
            raw_update=source_payload,
            original_text=message.text,
        )
        .on_conflict_do_nothing(constraint="uq_capture_telegram_update")
        .returning(RawCapture.id)
    )
    inserted_id = (await session.execute(statement)).scalar_one_or_none()

    if inserted_id is None:
        capture = await session.scalar(
            select(RawCapture).where(
                RawCapture.user_id == user_id,
                RawCapture.telegram_bot_id == bot_id,
                RawCapture.telegram_update_id == update.update_id,
            )
        )
        if capture is None:
            raise RuntimeError("Existing Telegram capture could not be loaded")
        job = await session.scalar(
            select(ProcessingJob).where(
                ProcessingJob.raw_capture_id == capture.id,
                ProcessingJob.kind == JobKind.NORMALIZE_TEXT,
            )
        )
        return capture, job, False

    capture = await session.get(RawCapture, inserted_id)
    if capture is None:
        raise RuntimeError("Inserted Telegram capture could not be loaded")

    job = None
    if message.text is not None:
        job = ProcessingJob(
            user_id=user_id,
            raw_capture_id=capture.id,
            kind=JobKind.NORMALIZE_TEXT,
        )
        session.add(job)
        await session.flush()
    return capture, job, True
