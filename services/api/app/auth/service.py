from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_session_token, new_session_token, verify_password
from app.models import Session, User


def normalize_email(email: str) -> str:
    return email.strip().casefold()


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def create_session(
    session: AsyncSession, user: User, ttl_seconds: int
) -> tuple[str, Session]:
    token = new_session_token()
    record = Session(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
    )
    session.add(record)
    await session.flush()
    return token, record


async def resolve_session(session: AsyncSession, token: str) -> User | None:
    record = await session.scalar(
        select(Session).where(
            Session.token_hash == hash_session_token(token),
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(UTC),
        )
    )
    if record is None:
        return None
    return await session.get(User, record.user_id)


async def revoke_session(session: AsyncSession, token: str) -> None:
    record = await session.scalar(
        select(Session).where(
            Session.token_hash == hash_session_token(token),
            Session.revoked_at.is_(None),
        )
    )
    if record is not None:
        record.revoked_at = datetime.now(UTC)
