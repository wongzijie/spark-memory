import uuid

import pytest

from app.jobs.dispatcher import STREAM, publish_job, recover_queued_jobs
from app.models import JobKind, ProcessingJob
from app.redis import create_redis


@pytest.fixture
async def redis_client():
    from app.config import get_settings

    client = create_redis(get_settings())
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def test_publish_job_writes_job_id_to_stream(redis_client):
    job_id = uuid.uuid4()

    await publish_job(redis_client, job_id)

    messages = await redis_client.xrange(STREAM)
    assert len(messages) == 1
    assert messages[0][1] == {"job_id": str(job_id)}


async def test_recover_queued_jobs_republishes_database_rows(
    db_session, user, raw_capture, redis_client
):
    job = ProcessingJob(
        user_id=user.id,
        raw_capture_id=raw_capture.id,
        kind=JobKind.NORMALIZE_TEXT,
    )
    db_session.add(job)
    await db_session.flush()

    recovered = await recover_queued_jobs(db_session, redis_client)

    assert recovered == 1
    messages = await redis_client.xrange(STREAM)
    assert messages[0][1] == {"job_id": str(job.id)}
