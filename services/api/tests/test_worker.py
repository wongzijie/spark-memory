from unittest.mock import AsyncMock

import pytest
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import func, select

from app.jobs.worker import normalize_text, process_job, read_messages
from app.models import JobKind, JobState, NormalizedContent, ProcessingJob, RawCapture


@pytest.fixture
async def queued_text_job(db_session, user, raw_capture):
    job = ProcessingJob(
        user_id=user.id,
        raw_capture_id=raw_capture.id,
        kind=JobKind.NORMALIZE_TEXT,
    )
    db_session.add(job)
    await db_session.flush()
    return job


def test_normalize_text_changes_line_endings_but_preserves_spacing():
    assert normalize_text("  第一条\r\n保留  空格  ") == "  第一条\n保留  空格  "


def test_normalize_text_uses_unicode_nfc():
    assert normalize_text("Cafe\u0301") == "Café"


async def test_processing_same_job_twice_creates_one_derivation(db_session, queued_text_job):
    first = await process_job(db_session, queued_text_job.id)
    second = await process_job(db_session, queued_text_job.id)

    assert first.state == JobState.PROCESSED
    assert second.state == JobState.PROCESSED
    count = await db_session.scalar(
        select(func.count())
        .select_from(NormalizedContent)
        .where(NormalizedContent.raw_capture_id == queued_text_job.raw_capture_id)
    )
    assert count == 1


async def test_processing_never_changes_raw_text(db_session, raw_capture, queued_text_job):
    raw_capture.original_text = "  第一条\r\n保留  空格  "
    expected = raw_capture.original_text
    await db_session.flush()

    await process_job(db_session, queued_text_job.id)
    await db_session.refresh(raw_capture)

    assert raw_capture.original_text == expected
    derivation = await db_session.scalar(
        select(NormalizedContent).where(NormalizedContent.raw_capture_id == raw_capture.id)
    )
    assert derivation is not None
    assert derivation.normalized_text == "  第一条\n保留  空格  "


async def test_non_text_job_fails_with_stable_error_code(db_session, user):
    capture = RawCapture(
        user_id=user.id,
        telegram_bot_id="bot-1",
        telegram_update_id=99,
        telegram_message_id=100,
        telegram_chat_id=3,
        telegram_user_id=4,
        raw_update={"update_id": 99},
        original_text=None,
    )
    db_session.add(capture)
    await db_session.flush()
    job = ProcessingJob(
        user_id=user.id,
        raw_capture_id=capture.id,
        kind=JobKind.NORMALIZE_TEXT,
    )
    db_session.add(job)
    await db_session.flush()

    result = await process_job(db_session, job.id)

    assert result.state == JobState.FAILED
    assert result.last_error_code == "unsupported_content"
    assert result.attempts == 1


async def test_idle_stream_timeout_is_treated_as_an_empty_poll():
    redis = AsyncMock()
    redis.xreadgroup.side_effect = RedisTimeoutError("idle stream")

    assert await read_messages(redis, "worker-1") == []
