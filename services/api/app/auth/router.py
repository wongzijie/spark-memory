from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import CurrentUserResponse, LoginRequest
from app.auth.service import authenticate, create_session, revoke_session
from app.dependencies import get_db_session, require_user
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(require_user)]


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(payload: LoginRequest, request: Request, session: DatabaseSession) -> Response:
    user = await authenticate(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    settings = request.app.state.settings
    token, _ = await create_session(session, user, settings.session_ttl_seconds)
    await session.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: DatabaseSession) -> Response:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    if token is not None:
        await revoke_session(session, token)
        await session.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email, timezone=user.timezone)
