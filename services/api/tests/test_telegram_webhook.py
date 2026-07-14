from copy import deepcopy

import pytest
from sqlalchemy import func, select

from app.models import ProcessingJob, RawCapture, User
from app.telegram.client import TelegramClient

TEST_PATH_SECRET = "test-path-secret-that-is-not-real-0001"
TEST_HEADER_SECRET = "test-header-secret-that-is-not-real-01"

TELEGRAM_UPDATE = {
    "update_id": 1001,
    "message": {
        "message_id": 88,
        "date": 1784020000,
        "chat": {"id": 9988, "type": "private"},
        "from": {"id": 7788, "is_bot": False, "first_name": "Owner"},
        "text": "  第一条 Spark\r\n保留段落  ",
    },
}


@pytest.fixture
async def telegram_admin(db_session):
    record = User(email="owner@example.com", password_hash="not-used-in-this-test")
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.fixture
def telegram_headers():
    return {"X-Telegram-Bot-Api-Secret-Token": TEST_HEADER_SECRET}


@pytest.fixture(autouse=True)
def acknowledgement_calls(monkeypatch):
    calls = []

    async def fake_send_message(self, chat_id, text):
        calls.append({"chat_id": chat_id, "text": text})
        return {"message_id": 1}

    monkeypatch.setattr(TelegramClient, "send_message", fake_send_message)
    return calls


async def test_webhook_rejects_wrong_header(client, db_session, telegram_admin):
    response = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=TELEGRAM_UPDATE,
    )

    assert response.status_code == 404
    assert await db_session.scalar(select(func.count()).select_from(RawCapture)) == 0


async def test_webhook_rejects_wrong_path_secret(
    client, db_session, telegram_admin, telegram_headers
):
    response = await client.post(
        "/api/telegram/webhook/wrong-path-secret",
        json=TELEGRAM_UPDATE,
        headers=telegram_headers,
    )

    assert response.status_code == 404
    assert await db_session.scalar(select(func.count()).select_from(RawCapture)) == 0


async def test_webhook_rejects_unconfigured_sender(
    client, db_session, telegram_admin, telegram_headers
):
    payload = deepcopy(TELEGRAM_UPDATE)
    payload["message"]["from"]["id"] = 9999

    response = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=payload,
        headers=telegram_headers,
    )

    assert response.status_code == 404
    assert await db_session.scalar(select(func.count()).select_from(RawCapture)) == 0


async def test_duplicate_update_creates_one_capture_and_job(
    client,
    db_session,
    telegram_admin,
    telegram_headers,
    acknowledgement_calls,
):
    first = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=TELEGRAM_UPDATE,
        headers=telegram_headers,
    )
    second = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=TELEGRAM_UPDATE,
        headers=telegram_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert await db_session.scalar(select(func.count()).select_from(RawCapture)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ProcessingJob)) == 1
    assert len(acknowledgement_calls) == 1


async def test_webhook_preserves_raw_payload_and_text(
    client, db_session, telegram_admin, telegram_headers
):
    payload = deepcopy(TELEGRAM_UPDATE)
    payload["update_id"] = 1002
    payload["message"]["custom_source_field"] = {"kept": True}

    response = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=payload,
        headers=telegram_headers,
    )

    assert response.status_code == 200
    capture = await db_session.scalar(
        select(RawCapture).where(RawCapture.telegram_update_id == 1002)
    )
    assert capture is not None
    assert capture.raw_update == payload
    assert capture.original_text == payload["message"]["text"]


async def test_non_text_update_is_preserved_without_job(
    client, db_session, telegram_admin, telegram_headers
):
    payload = deepcopy(TELEGRAM_UPDATE)
    payload["update_id"] = 1003
    payload["message"].pop("text")
    payload["message"]["photo"] = [{"file_id": "photo-1", "width": 800, "height": 600}]

    response = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=payload,
        headers=telegram_headers,
    )

    assert response.status_code == 200
    assert response.json()["created"] is True
    capture = await db_session.scalar(
        select(RawCapture).where(RawCapture.telegram_update_id == 1003)
    )
    assert capture is not None
    assert capture.raw_update == payload
    assert capture.original_text is None
    assert await db_session.scalar(select(func.count()).select_from(ProcessingJob)) == 0


async def test_acknowledgement_runs_after_database_commit(
    client, db_session, telegram_admin, telegram_headers, monkeypatch
):
    observed_counts = []

    async def observe_commit(self, chat_id, text):
        count = await db_session.scalar(select(func.count()).select_from(RawCapture))
        observed_counts.append(count)
        return {"message_id": 1}

    monkeypatch.setattr(TelegramClient, "send_message", observe_commit)
    payload = deepcopy(TELEGRAM_UPDATE)
    payload["update_id"] = 1004

    response = await client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}",
        json=payload,
        headers=telegram_headers,
    )

    assert response.status_code == 200
    assert observed_counts == [1]
