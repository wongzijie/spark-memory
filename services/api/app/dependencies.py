from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import resolve_session
from app.models import User


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


async def require_user(request: Request) -> User:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    async with request.app.state.sessionmaker() as session:
        user = await resolve_session(session, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
