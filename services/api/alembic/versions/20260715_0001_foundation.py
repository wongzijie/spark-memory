"""Create the foundation persistence schema.

Revision ID: 20260715_0001
Revises:
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260715_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    job_kind = postgresql.ENUM("normalize_text", name="job_kind", create_type=False)
    job_state = postgresql.ENUM(
        "queued",
        "processing",
        "processed",
        "needs_attention",
        "failed",
        name="job_state",
        create_type=False,
    )
    job_kind.create(op.get_bind(), checkfirst=True)
    job_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "raw_captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_bot_id", sa.String(length=128), nullable=False),
        sa.Column("telegram_update_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_update", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "telegram_bot_id",
            "telegram_update_id",
            name="uq_capture_telegram_update",
        ),
    )
    op.create_table(
        "normalized_contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_capture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["raw_capture_id"], ["raw_captures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_capture_id", name="uq_normalized_capture"),
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_capture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", job_kind, nullable=False),
        sa.Column("state", job_state, nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["raw_capture_id"], ["raw_captures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_capture_id", "kind", name="uq_capture_job_kind"),
    )


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("normalized_contents")
    op.drop_table("raw_captures")
    op.drop_table("sessions")
    op.drop_table("users")
    postgresql.ENUM(name="job_state").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="job_kind").drop(op.get_bind(), checkfirst=True)
