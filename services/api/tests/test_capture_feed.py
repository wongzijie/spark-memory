from datetime import UTC, datetime, timedelta

from app.auth.security import hash_password
from app.models import (
    JobKind,
    JobState,
    NormalizedContent,
    ProcessingJob,
    RawCapture,
    User,
)

PASSWORD = "correct horse battery staple"


async def create_feed_user(db_session, email: str) -> User:
    user = User(email=email, password_hash=hash_password(PASSWORD))
    db_session.add(user)
    await db_session.flush()
    return user


def create_capture(user: User, update_id: int, created_at: datetime) -> RawCapture:
    return RawCapture(
        user_id=user.id,
        telegram_bot_id="bot-1",
        telegram_update_id=update_id,
        telegram_message_id=update_id,
        telegram_chat_id=3,
        telegram_user_id=4,
        raw_update={"update_id": update_id},
        original_text=f"Spark {update_id}",
        created_at=created_at,
        updated_at=created_at,
    )


async def log_in(client, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 204


async def test_capture_feed_requires_authentication(client, db_session):
    response = await client.get("/api/captures?limit=50")

    assert response.status_code == 401


async def test_capture_feed_is_user_scoped(client, db_session):
    owner = await create_feed_user(db_session, "owner@example.com")
    other = await create_feed_user(db_session, "other@example.com")
    now = datetime.now(UTC)
    owned_capture = create_capture(owner, 11, now)
    other_capture = create_capture(other, 12, now + timedelta(seconds=1))
    db_session.add_all([owned_capture, other_capture])
    await db_session.flush()
    db_session.add_all(
        [
            NormalizedContent(
                user_id=owner.id,
                raw_capture_id=owned_capture.id,
                normalized_text="Spark 11",
                language=None,
            ),
            ProcessingJob(
                user_id=owner.id,
                raw_capture_id=owned_capture.id,
                kind=JobKind.NORMALIZE_TEXT,
                state=JobState.PROCESSED,
            ),
        ]
    )
    await db_session.commit()
    await log_in(client, owner.email)

    response = await client.get("/api/captures?limit=50")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0] == {
        "id": str(owned_capture.id),
        "received_at": owned_capture.created_at.isoformat().replace("+00:00", "Z"),
        "original_text": "Spark 11",
        "normalized_text": "Spark 11",
        "processing_state": "processed",
        "source": "telegram",
    }
    assert body["next_cursor"] is None


async def test_capture_feed_cursor_has_no_duplicates(client, db_session):
    owner = await create_feed_user(db_session, "owner@example.com")
    now = datetime.now(UTC)
    captures = [
        create_capture(owner, update_id, now + timedelta(seconds=update_id))
        for update_id in (21, 22, 23)
    ]
    db_session.add_all(captures)
    await db_session.commit()
    await log_in(client, owner.email)

    first = await client.get("/api/captures?limit=2")
    assert first.status_code == 200
    first_body = first.json()
    assert [item["original_text"] for item in first_body["items"]] == ["Spark 23", "Spark 22"]
    assert first_body["next_cursor"] is not None

    second = await client.get(
        "/api/captures",
        params={"limit": 2, "cursor": first_body["next_cursor"]},
    )

    assert second.status_code == 200
    second_body = second.json()
    assert [item["original_text"] for item in second_body["items"]] == ["Spark 21"]
    assert second_body["next_cursor"] is None
