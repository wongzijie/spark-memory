import base64
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, require_user
from app.models import JobKind, JobState, NormalizedContent, ProcessingJob, RawCapture, User

router = APIRouter(prefix="/api/captures", tags=["captures"])


class CaptureItem(BaseModel):
    id: uuid.UUID
    received_at: datetime
    original_text: str | None
    normalized_text: str | None
    processing_state: JobState
    source: Literal["telegram"] = "telegram"


class CaptureFeedResponse(BaseModel):
    items: list[CaptureItem]
    next_cursor: str | None


def encode_cursor(received_at: datetime, capture_id: uuid.UUID) -> str:
    value = f"{received_at.isoformat()}|{capture_id}".encode()
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, uuid.UUID]:
    try:
        padding = "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(f"{value}{padding}").decode()
        received_at, capture_id = decoded.rsplit("|", 1)
        return datetime.fromisoformat(received_at), uuid.UUID(capture_id)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capture cursor",
        ) from None


@router.get("", response_model=CaptureFeedResponse)
async def capture_feed(
    current_user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> CaptureFeedResponse:
    statement = (
        select(RawCapture, NormalizedContent.normalized_text, ProcessingJob.state)
        .outerjoin(
            NormalizedContent,
            and_(
                NormalizedContent.raw_capture_id == RawCapture.id,
                NormalizedContent.user_id == current_user.id,
            ),
        )
        .outerjoin(
            ProcessingJob,
            and_(
                ProcessingJob.raw_capture_id == RawCapture.id,
                ProcessingJob.user_id == current_user.id,
                ProcessingJob.kind == JobKind.NORMALIZE_TEXT,
            ),
        )
        .where(RawCapture.user_id == current_user.id)
        .order_by(RawCapture.created_at.desc(), RawCapture.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        cursor_time, cursor_id = decode_cursor(cursor)
        statement = statement.where(
            or_(
                RawCapture.created_at < cursor_time,
                and_(RawCapture.created_at == cursor_time, RawCapture.id < cursor_id),
            )
        )

    rows = list((await session.execute(statement)).all())
    page = rows[:limit]
    items = [
        CaptureItem(
            id=capture.id,
            received_at=capture.created_at,
            original_text=capture.original_text,
            normalized_text=normalized_text,
            processing_state=job_state or JobState.NEEDS_ATTENTION,
        )
        for capture, normalized_text, job_state in page
    ]
    next_cursor = None
    if len(rows) > limit and page:
        last_capture = page[-1][0]
        next_cursor = encode_cursor(last_capture.created_at, last_capture.id)
    return CaptureFeedResponse(items=items, next_cursor=next_cursor)
