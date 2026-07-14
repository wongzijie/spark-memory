import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class JobState(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    NEEDS_ATTENTION = "needs_attention"
    FAILED = "failed"


class JobKind(StrEnum):
    NORMALIZE_TEXT = "normalize_text"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", nullable=False)


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RawCapture(TimestampMixin, Base):
    __tablename__ = "raw_captures"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "telegram_bot_id",
            "telegram_update_id",
            name="uq_capture_telegram_update",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    telegram_bot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_update_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    raw_update: Mapped[dict] = mapped_column(JSONB, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text)


class NormalizedContent(TimestampMixin, Base):
    __tablename__ = "normalized_contents"
    __table_args__ = (UniqueConstraint("raw_capture_id", name="uq_normalized_capture"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    raw_capture_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_captures.id", ondelete="CASCADE"), nullable=False
    )
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16))


class ProcessingJob(TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (UniqueConstraint("raw_capture_id", "kind", name="uq_capture_job_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    raw_capture_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_captures.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[JobKind] = mapped_column(
        Enum(
            JobKind,
            name="job_kind",
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
    )
    state: Mapped[JobState] = mapped_column(
        Enum(
            JobState,
            name="job_state",
            values_callable=lambda members: [member.value for member in members],
        ),
        default=JobState.QUEUED,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(Text)
