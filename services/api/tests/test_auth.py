from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.auth.security import hash_password, hash_session_token, verify_password
from app.models import Session as UserSession
from app.models import User

PASSWORD = "correct horse battery staple"


@pytest.fixture
async def admin_user(db_session):
    record = User(email="owner@example.com", password_hash=hash_password(PASSWORD))
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


def test_password_hash_round_trip():
    encoded = hash_password(PASSWORD)

    assert encoded != PASSWORD
    assert verify_password(PASSWORD, encoded) is True
    assert verify_password("wrong password", encoded) is False


async def test_login_sets_http_only_cookie_and_stores_only_token_hash(
    client, db_session, admin_user
):
    response = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": PASSWORD},
    )

    assert response.status_code == 204
    assert "spark_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    token = client.cookies.get("spark_session")
    assert token is not None
    record = await db_session.scalar(select(UserSession))
    assert record is not None
    assert record.token_hash == hash_session_token(token)
    assert record.token_hash != token


async def test_invalid_login_does_not_set_cookie(client, admin_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "wrong password"},
    )

    assert response.status_code == 401
    assert client.cookies.get("spark_session") is None


async def test_me_returns_current_user(client, admin_user):
    login = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": PASSWORD},
    )
    assert login.status_code == 204

    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(admin_user.id),
        "email": "owner@example.com",
        "timezone": "Asia/Shanghai",
    }


async def test_logout_revokes_session_and_clears_cookie(client, db_session, admin_user):
    login = await client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": PASSWORD},
    )
    assert login.status_code == 204
    token = client.cookies.get("spark_session")
    assert token is not None

    response = await client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    record = await db_session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )
    assert record is not None
    await db_session.refresh(record)
    assert record.revoked_at is not None
    assert client.cookies.get("spark_session") is None


async def test_expired_session_is_rejected(client, db_session, admin_user):
    token = "expired-session-token"
    db_session.add(
        UserSession(
            user_id=admin_user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    await db_session.commit()
    client.cookies.set("spark_session", token)

    response = await client.get("/api/auth/me")

    assert response.status_code == 401


async def test_me_requires_a_session(client, db_session):
    response = await client.get("/api/auth/me")

    assert response.status_code == 401
