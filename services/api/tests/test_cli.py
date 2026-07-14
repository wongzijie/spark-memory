import io

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from app.auth.security import verify_password
from app.cli import main
from app.config import get_settings
from app.models import User

PASSWORD = "correct horse battery staple"


@pytest.fixture
def migrated_database():
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


def test_create_admin_prompts_twice_and_hashes_password(monkeypatch, migrated_database, capsys):
    answers = iter([PASSWORD, PASSWORD])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: next(answers))

    exit_code = main(["create-admin", "--email", "OWNER@example.com"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "owner@example.com" in captured.out
    assert PASSWORD not in captured.out
    engine = create_engine(get_settings().database_url)
    try:
        with Session(engine) as session:
            user = session.scalar(select(User))
            assert user is not None
            assert verify_password(PASSWORD, user.password_hash)
    finally:
        engine.dispose()


def test_create_admin_reads_exactly_one_stdin_line(migrated_database, capsys):
    stream = io.StringIO(f"{PASSWORD}\nthis line must remain\n")

    exit_code = main(
        ["create-admin", "--email", "owner@example.com", "--password-stdin"],
        stdin=stream,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert PASSWORD not in captured.out
    assert stream.read() == "this line must remain\n"


def test_create_admin_accepts_powershell_utf8_bom(migrated_database, capsys):
    exit_code = main(
        ["create-admin", "--email", "owner@example.com", "--password-stdin"],
        stdin=io.StringIO(f"\ufeff{PASSWORD}\r\n"),
    )

    assert exit_code == 0
    engine = create_engine(get_settings().database_url)
    try:
        with Session(engine) as session:
            user = session.scalar(select(User))
            assert user is not None
            assert verify_password(PASSWORD, user.password_hash)
    finally:
        engine.dispose()


def test_create_admin_refuses_a_second_account(migrated_database, capsys):
    first = main(
        ["create-admin", "--email", "owner@example.com", "--password-stdin"],
        stdin=io.StringIO(f"{PASSWORD}\n"),
    )
    second = main(
        ["create-admin", "--email", "other@example.com", "--password-stdin"],
        stdin=io.StringIO(f"{PASSWORD}\n"),
    )

    captured = capsys.readouterr()
    assert first == 0
    assert second != 0
    assert "already exists" in captured.err
    assert PASSWORD not in captured.out
    assert PASSWORD not in captured.err


def test_create_admin_rejects_mismatched_prompt_passwords(monkeypatch, migrated_database, capsys):
    answers = iter([PASSWORD, "different password"])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: next(answers))

    exit_code = main(["create-admin", "--email", "owner@example.com"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "do not match" in captured.err


def test_register_webhook_command_uses_configured_bot(monkeypatch, capsys):
    async def fake_register_webhook_account():
        return "test-bot"

    monkeypatch.setattr(
        "app.cli.register_webhook_account",
        fake_register_webhook_account,
        raising=False,
    )

    exit_code = main(["register-webhook"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "test-bot" in captured.out
    assert "test-bot-token" not in captured.out
