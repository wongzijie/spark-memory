import uuid

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobState, ProcessingJob

STREAM = "spark:jobs"


async def publish_job(redis: Redis, job_id: uuid.UUID) -> None:
    await redis.xadd(STREAM, {"job_id": str(job_id)})


async def recover_queued_jobs(session: AsyncSession, redis: Redis, limit: int = 100) -> int:
    ids = list(
        await session.scalars(
            select(ProcessingJob.id)
            .where(ProcessingJob.state == JobState.QUEUED)
            .order_by(ProcessingJob.created_at)
            .limit(limit)
        )
    )
    for job_id in ids:
        await publish_job(redis, job_id)
    return len(ids)
