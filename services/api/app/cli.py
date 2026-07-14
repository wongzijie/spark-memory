import argparse
import asyncio
import getpass
import sys
from collections.abc import Coroutine, Sequence
from typing import Any, TextIO

from sqlalchemy import delete, func, select

from app.auth.security import hash_password
from app.auth.service import normalize_email
from app.config import get_settings
from app.db import create_engine_and_sessionmaker
from app.models import Session as UserSession
from app.models import User
from app.telegram.client import TelegramClient


class CliError(Exception):
    pass


def run_async[Result](coroutine: Coroutine[Any, Any, Result]) -> Result:
    if sys.platform == "win32":
        return asyncio.run(coroutine, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coroutine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin = subparsers.add_parser("create-admin")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--password-stdin", action="store_true")
    configure_admin = subparsers.add_parser("configure-admin")
    configure_admin.add_argument("--email", required=True)
    configure_admin.add_argument("--password-stdin", action="store_true")
    subparsers.add_parser("register-webhook")
    return parser


def read_password(password_stdin: bool, stdin: TextIO) -> str:
    if password_stdin:
        password = stdin.readline().removeprefix("\ufeff").rstrip("\r\n")
        if not password:
            raise CliError("Password from stdin must not be empty")
        return password

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise CliError("Passwords do not match")
    if not password:
        raise CliError("Password must not be empty")
    return password


async def create_admin_account(email: str, password: str) -> User:
    settings = get_settings()
    engine, session_factory = create_engine_and_sessionmaker(settings)
    try:
        async with session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(User))
            if count:
                raise CliError("An admin account already exists")
            user = User(
                email=normalize_email(email),
                password_hash=hash_password(password),
                timezone=settings.default_timezone,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    finally:
        await engine.dispose()


async def configure_admin_account(email: str, password: str) -> User:
    settings = get_settings()
    engine, session_factory = create_engine_and_sessionmaker(settings)
    try:
        async with session_factory() as session:
            user = await session.scalar(select(User).order_by(User.created_at).limit(1))
            if user is None:
                user = User(
                    email=normalize_email(email),
                    password_hash=hash_password(password),
                    timezone=settings.default_timezone,
                )
                session.add(user)
            else:
                user.email = normalize_email(email)
                user.password_hash = hash_password(password)
                await session.execute(delete(UserSession))
            await session.commit()
            await session.refresh(user)
            return user
    finally:
        await engine.dispose()


async def register_webhook_account() -> str:
    settings = get_settings()
    async with TelegramClient(settings.telegram_bot_token) as telegram:
        await telegram.set_webhook(
            public_base_url=str(settings.public_base_url),
            path_secret=settings.telegram_webhook_path_secret.get_secret_value(),
            header_secret=settings.telegram_webhook_header_secret.get_secret_value(),
        )
    return settings.telegram_bot_id


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    output: TextIO | None = None,
    error: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    output = output or sys.stdout
    error = error or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create-admin":
            password = read_password(args.password_stdin, stdin)
            user = run_async(create_admin_account(args.email, password))
            print(f"Created admin {user.email} ({user.id})", file=output)
            return 0
        if args.command == "configure-admin":
            password = read_password(args.password_stdin, stdin)
            user = run_async(configure_admin_account(args.email, password))
            print(f"Configured admin {user.email} ({user.id})", file=output)
            return 0
        if args.command == "register-webhook":
            bot_id = run_async(register_webhook_account())
            print(f"Registered webhook for bot {bot_id}", file=output)
            return 0
        raise CliError(f"Unsupported command: {args.command}")
    except CliError as exc:
        print(str(exc), file=error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
