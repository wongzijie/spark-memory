import asyncio
import logging
import os
import socket
import sys
import time
import unicodedata
import uuid

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db import create_engine_and_sessionmaker
from app.jobs.dispatcher import STREAM, recover_queued_jobs
from app.models import JobState, NormalizedContent, ProcessingJob, RawCapture
from app.redis import create_redis

logger = logging.getLogger(__name__)
GROUP = "spark-workers"


def normalize_text(value: str) -> str:
    line_normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", line_normalized)


async def process_job(session: AsyncSession, job_id: uuid.UUID) -> ProcessingJob:
    job = await session.scalar(
        select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update(skip_locked=True)
    )
    if job is None:
        raise LookupError(f"processing job not found: {job_id}")
    if job.state == JobState.PROCESSED:
        return job

    job.state = JobState.PROCESSING
    job.attempts += 1
    raw = await session.get(RawCapture, job.raw_capture_id)
    if raw is None or raw.original_text is None:
        job.state = JobState.FAILED
        job.last_error_code = "unsupported_content"
        job.last_error_message = "Text normalization requires original_text"
        await session.commit()
        return job

    statement = (
        insert(NormalizedContent)
        .values(
            user_id=job.user_id,
            raw_capture_id=raw.id,
            normalized_text=normalize_text(raw.original_text),
            language=None,
        )
        .on_conflict_do_nothing(constraint="uq_normalized_capture")
    )
    await session.execute(statement)
    job.state = JobState.PROCESSED
    job.last_error_code = None
    job.last_error_message = None
    await session.commit()
    return job


async def ensure_consumer_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def read_messages(
    redis: Redis,
    consumer: str,
) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
    try:
        return await redis.xreadgroup(
            GROUP,
            consumer,
            streams={STREAM: ">"},
            count=10,
            block=5_000,
        )
    except RedisTimeoutError:
        # redis-py can end a blocking stream read at the same boundary as Redis.
        # An idle stream is a normal poll result, not a worker failure.
        return []


async def record_processing_failure(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: uuid.UUID,
    error: Exception,
) -> None:
    async with session_factory() as session:
        job = await session.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .with_for_update(skip_locked=True)
        )
        if job is None or job.state == JobState.PROCESSED:
            return
        job.attempts += 1
        job.state = JobState.FAILED
        job.last_error_code = type(error).__name__[:64]
        job.last_error_message = "Worker processing failed"
        await session.commit()


async def run_worker() -> None:
    settings = get_settings()
    engine, session_factory = create_engine_and_sessionmaker(settings)
    redis = create_redis(settings)
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    try:
        await ensure_consumer_group(redis)
        async with session_factory() as session:
            await recover_queued_jobs(session, redis)
        last_recovery = time.monotonic()

        while True:
            messages = await read_messages(redis, consumer)
            for _, entries in messages:
                for message_id, fields in entries:
                    try:
                        job_id = uuid.UUID(fields["job_id"])
                    except (KeyError, ValueError):
                        await redis.xack(STREAM, GROUP, message_id)
                        continue
                    try:
                        async with session_factory() as session:
                            await process_job(session, job_id)
                    except Exception as exc:
                        logger.error("Job %s failed: %s", job_id, type(exc).__name__)
                        await record_processing_failure(session_factory, job_id, exc)
                    await redis.xack(STREAM, GROUP, message_id)

            if time.monotonic() - last_recovery >= 30:
                async with session_factory() as session:
                    await recover_queued_jobs(session, redis)
                last_recovery = time.monotonic()
    finally:
        await redis.aclose()
        await engine.dispose()


def main() -> None:
    if sys.platform == "win32":
        asyncio.run(run_worker(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()
