import pytest
from sqlalchemy.exc import IntegrityError

from app.models import JobKind, ProcessingJob, RawCapture, User


async def test_duplicate_telegram_update_is_rejected(db_session):
    user = User(email="duplicate@example.com", password_hash="not-used-in-this-test")
    db_session.add(user)
    await db_session.flush()
    values = {
        "user_id": user.id,
        "telegram_bot_id": "bot-1",
        "telegram_update_id": 42,
        "telegram_chat_id": 7,
        "telegram_user_id": 9,
        "raw_update": {"update_id": 42},
        "original_text": "原始内容  不修改",
    }
    db_session.add_all([RawCapture(**values), RawCapture(**values)])

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_one_normalization_job_per_capture(db_session, user, raw_capture):
    first = ProcessingJob(
        user_id=user.id,
        raw_capture_id=raw_capture.id,
        kind=JobKind.NORMALIZE_TEXT,
    )
    second = ProcessingJob(
        user_id=user.id,
        raw_capture_id=raw_capture.id,
        kind=JobKind.NORMALIZE_TEXT,
    )
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_raw_capture_preserves_source_payload_and_text(db_session, raw_capture):
    expected_payload = dict(raw_capture.raw_update)
    expected_text = raw_capture.original_text

    await db_session.commit()
    await db_session.refresh(raw_capture)

    assert raw_capture.raw_update == expected_payload
    assert raw_capture.original_text == expected_text
