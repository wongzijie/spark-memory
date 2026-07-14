# Spark Memory Foundation and Telegram Text Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable Spark Memory vertical slice: a single admin logs in, Telegram text updates are authenticated and stored immutably, a Redis-backed worker creates normalized derived content, and the Dashboard shows the capture and processing state.

**Architecture:** FastAPI owns the API, Telegram Webhook, sessions, PostgreSQL writes, and worker entrypoint. PostgreSQL is the source of truth; Redis Streams only wakes workers, and queued database jobs are recoverable if stream publication fails. Next.js proxies `/api` to FastAPI so the browser uses one origin and a secure HTTP-only session cookie.

**Tech Stack:** Python 3.13, FastAPI 0.139.0, Pydantic 2.13.4, SQLAlchemy 2.0.51, Alembic 1.18.5, psycopg 3.3.4, redis-py 8.0.1, PostgreSQL 18 + pgvector 0.8.2, Redis 8, Node.js 24, pnpm 11.13.0, Next.js 16.2.10, React 19.2.7, TypeScript 7.0.2, Vitest 4.1.10, Playwright 1.61.1, Docker Compose.

## Global Constraints

- Preserve the raw Telegram update and original text exactly; normalized content belongs in a separate table.
- Scope every database row and query by `user_id`, even with one MVP account.
- A Telegram update is idempotent on `(user_id, telegram_bot_id, telegram_update_id)`.
- Persist `RawCapture` and `ProcessingJob` in one database transaction before sending an acknowledgement.
- Return a Telegram 2xx response even if Redis publication or the acknowledgement message fails after persistence; queued jobs remain recoverable from PostgreSQL.
- Use UTC in storage and `Asia/Shanghai` only as the initial account display timezone.
- Never log or return the Telegram Bot Token, password, session token, database password, or Webhook secrets.
- Pin direct dependencies and commit `uv.lock` plus `pnpm-lock.yaml`.
- Use TDD: observe each focused test fail before adding its implementation.
- Run Python lint/tests and web lint/type/tests before every task commit.
- Milestone 1 uses environment-provided Telegram credentials. Dashboard-managed BYOK is Milestone 2, with no throwaway credential API added here.
- Follow the current official requirements: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI version pinning](https://fastapi.tiangolo.com/deployment/versions/), [Telegram Webhook secret token](https://core.telegram.org/bots/api#setwebhook), and [pgvector Docker support](https://github.com/pgvector/pgvector#docker).

---

## Milestone Boundary

This plan deliberately ends after durable plain-text capture and authenticated viewing. Memory books, LLM classification, Settings/BYOK, multimodal extraction, Running-up, Tavily, and production backup automation remain in the named later milestones in `2026-07-14-spark-memory-mvp-roadmap.md`.

## File and Responsibility Map

```text
.
├── .env.example                         # Non-secret configuration contract
├── compose.yml                          # PostgreSQL, Redis, API, worker, and web
├── package.json                         # Root pnpm scripts and version pin
├── pnpm-workspace.yaml                  # Web workspace declaration
├── .github/workflows/ci.yml             # Python and web validation
├── apps/web/
│   ├── next.config.ts                   # Same-origin /api proxy
│   ├── package.json                     # Next.js dependencies and scripts
│   ├── src/app/login/page.tsx           # Admin login form
│   ├── src/app/page.tsx                 # Protected capture feed
│   ├── src/app/globals.css              # Milestone UI tokens/layout
│   ├── src/components/capture-feed.tsx  # Capture list rendering
│   └── src/lib/api.ts                   # Typed API client and schemas
└── services/api/
    ├── pyproject.toml                   # Pinned API/runtime/test dependencies
    ├── uv.lock                          # Reproducible Python dependency lock
    ├── alembic.ini                      # Migration configuration
    ├── alembic/env.py                   # Async migration environment
    ├── alembic/versions/*_foundation.py # Initial product schema
    ├── app/main.py                      # FastAPI factory and lifespan
    ├── app/config.py                    # Validated environment settings
    ├── app/db.py                        # Async SQLAlchemy engine/session
    ├── app/redis.py                     # Redis connection factory
    ├── app/models.py                    # Base, user, session, capture, derivation, job
    ├── app/health/router.py             # Live/ready endpoints
    ├── app/auth/security.py             # Password/session hashing
    ├── app/auth/service.py              # Bootstrap, login, logout, current user
    ├── app/auth/router.py               # Auth HTTP endpoints
    ├── app/captures/service.py          # Atomic idempotent capture transaction
    ├── app/captures/router.py           # Authenticated capture feed endpoint
    ├── app/telegram/client.py            # getMe, setWebhook, sendMessage calls
    ├── app/telegram/schemas.py           # Telegram update parsing
    ├── app/telegram/router.py            # Secret/user checks and persistence flow
    ├── app/jobs/dispatcher.py            # Redis Stream publication/recovery
    ├── app/jobs/worker.py                # Job claim, normalization, completion
    ├── app/cli.py                        # Admin bootstrap and Webhook registration
    └── tests/                            # Unit/integration/API tests
```

## Public Interfaces Locked by This Plan

```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    session_cookie_name: str
    session_ttl_seconds: int
    session_cookie_secure: bool
    telegram_bot_token: SecretStr
    telegram_bot_id: str
    telegram_allowed_user_id: int
    telegram_webhook_path_secret: SecretStr
    telegram_webhook_header_secret: SecretStr
    public_base_url: AnyHttpUrl

async def create_capture_from_update(
    session: AsyncSession, *, user_id: UUID, bot_id: str, update: TelegramUpdate
) -> tuple[RawCapture, ProcessingJob, bool]:
    """Return capture, job, and created flag in the caller's transaction."""

async def publish_job(redis: Redis, job_id: UUID) -> None:
    """Publish a job id to the `spark:jobs` Redis Stream."""

async def process_job(session: AsyncSession, job_id: UUID) -> ProcessingJob:
    """Idempotently normalize a queued text capture and finish the job."""
```

HTTP contracts:

```text
GET    /health/live
GET    /health/ready
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
GET    /api/captures?limit=50&cursor=<received_at,id>
POST   /api/telegram/webhook/{path_secret}
```

---

### Task 1: Create the FastAPI Project and Liveness Contract

**Files:**
- Create: `.python-version`
- Create: `services/api/pyproject.toml`
- Create: `services/api/app/__init__.py`
- Create: `services/api/app/main.py`
- Create: `services/api/app/health/__init__.py`
- Create: `services/api/app/health/router.py`
- Create: `services/api/tests/conftest.py`
- Create: `services/api/tests/test_health.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`, `GET /health/live -> {"status": "ok"}`.
- Consumes: none.

- [ ] **Step 1: Write the failing liveness test**

```python
# services/api/tests/test_health.py
def test_liveness(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

```python
# services/api/tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client
```

- [ ] **Step 2: Create and lock the Python project, then verify the test fails**

```toml
# services/api/pyproject.toml
[project]
name = "spark-memory-api"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  "alembic==1.18.5",
  "fastapi==0.139.0",
  "httpx==0.28.1",
  "psycopg[binary,pool]==3.3.4",
  "pydantic==2.13.4",
  "pydantic-settings==2.14.2",
  "pwdlib[argon2]==0.3.0",
  "redis==8.0.1",
  "sqlalchemy[asyncio]==2.0.51",
  "uvicorn[standard]==0.51.0",
]

[dependency-groups]
dev = [
  "pytest==9.1.1",
  "pytest-asyncio==1.4.0",
  "ruff==0.15.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC"]
```

Run:

```powershell
Set-Location services/api
uv lock
uv run pytest tests/test_health.py -v
```

Create `.python-version` with this exact content before running the commands:

```text
3.13
```

Expected: collection fails because `app.main` does not exist.

- [ ] **Step 3: Implement the app factory and liveness route**

```python
# services/api/app/health/router.py
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# services/api/app/main.py
from fastapi import FastAPI

from app.health.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Spark Memory API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
```

Create empty `__init__.py` files at `app/__init__.py` and `app/health/__init__.py`.

- [ ] **Step 4: Run focused and static checks**

Run:

```powershell
Set-Location services/api
uv run pytest tests/test_health.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

Expected: one test passes; Ruff exits 0.

- [ ] **Step 5: Commit the API foundation**

```powershell
git add .python-version services/api
git commit -m "feat: scaffold Spark Memory API"
```

---

### Task 2: Add Validated Configuration and Service Readiness

**Files:**
- Create: `.env.example`
- Create: `compose.yml`
- Create: `services/api/app/config.py`
- Create: `services/api/app/db.py`
- Create: `services/api/app/redis.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/health/router.py`
- Create: `services/api/tests/test_config.py`
- Create: `services/api/tests/test_readiness.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`, `create_engine_and_sessionmaker(settings)`, `create_redis(settings)`, `GET /health/ready`.
- Consumes: `create_app()` from Task 1.

- [ ] **Step 1: Write failing configuration tests**

```python
# services/api/tests/test_config.py
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_require_real_secrets():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://spark:spark@localhost:5432/spark",
            redis_url="redis://localhost:6379/0",
            telegram_bot_token="short",
            telegram_bot_id="spark",
            telegram_allowed_user_id=1,
            telegram_webhook_path_secret="short",
            telegram_webhook_header_secret="short",
            public_base_url="https://example.com",
            _env_file=None,
        )


def test_settings_default_timezone_is_shanghai(valid_settings_data):
    settings = Settings(**valid_settings_data, _env_file=None)

    assert settings.default_timezone == "Asia/Shanghai"
```

```python
# services/api/tests/test_readiness.py
def test_readiness_checks_postgres_and_redis(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
```

Extend `tests/conftest.py` with:

```python
import pytest

from app.config import get_settings


@pytest.fixture
def valid_settings_data() -> dict[str, object]:
    return {
        "database_url": "postgresql+psycopg://spark:spark-local-only@localhost:5432/spark",
        "redis_url": "redis://localhost:6379/0",
        "telegram_bot_token": "test-bot-token-that-is-not-real-0000000001",
        "telegram_bot_id": "test-bot",
        "telegram_allowed_user_id": 7788,
        "telegram_webhook_path_secret": "test-path-secret-that-is-not-real-0001",
        "telegram_webhook_header_secret": "test-header-secret-that-is-not-real-01",
        "public_base_url": "https://example.invalid",
    }


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch, valid_settings_data):
    for name, value in valid_settings_data.items():
        monkeypatch.setenv(f"SPARK_{name.upper()}", str(value))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run: `uv run pytest tests/test_config.py -v`

Expected: import fails because `app.config` does not exist.

- [ ] **Step 3: Implement validated settings and connection factories**

```python
# services/api/app/config.py
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SPARK_", extra="ignore")

    app_env: str = "development"
    database_url: str
    redis_url: str
    default_timezone: str = "Asia/Shanghai"
    session_cookie_name: str = "spark_session"
    session_ttl_seconds: int = 604_800
    session_cookie_secure: bool = False
    telegram_bot_token: SecretStr = Field(min_length=32)
    telegram_bot_id: str = Field(min_length=1)
    telegram_allowed_user_id: int = Field(gt=0)
    telegram_webhook_path_secret: SecretStr = Field(min_length=32)
    telegram_webhook_header_secret: SecretStr = Field(min_length=32)
    public_base_url: AnyHttpUrl


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

```python
# services/api/app/db.py
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def create_engine_and_sessionmaker(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)
```

```python
# services/api/app/redis.py
from redis.asyncio import Redis

from app.config import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)
```

Replace `app/main.py` with:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import create_engine_and_sessionmaker
from app.health.router import router as health_router
from app.redis import create_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine, sessionmaker = create_engine_and_sessionmaker(settings)
    redis = create_redis(settings)
    app.state.settings = settings
    app.state.db_engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Spark Memory API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
```

Add readiness to `health/router.py`:

```python
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> dict[str, str]:
    async with request.app.state.sessionmaker() as session:
        await session.execute(text("SELECT 1"))
    await request.app.state.redis.ping()
    return {"status": "ready"}
```

- [ ] **Step 4: Add reproducible dependency services**

```yaml
# compose.yml
services:
  postgres:
    image: pgvector/pgvector:0.8.2-pg18-bookworm
    environment:
      POSTGRES_DB: spark
      POSTGRES_USER: spark
      POSTGRES_PASSWORD: spark-local-only
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U spark -d spark"]
      interval: 3s
      timeout: 3s
      retries: 20
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:8-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 20
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Create `.env.example` with harmless, nonfunctional values:

```dotenv
SPARK_APP_ENV=development
SPARK_DATABASE_URL=postgresql+psycopg://spark:spark-local-only@localhost:5432/spark
SPARK_REDIS_URL=redis://localhost:6379/0
SPARK_DEFAULT_TIMEZONE=Asia/Shanghai
SPARK_SESSION_COOKIE_NAME=spark_session
SPARK_SESSION_TTL_SECONDS=604800
SPARK_SESSION_COOKIE_SECURE=false
SPARK_TELEGRAM_BOT_TOKEN=replace-this-with-a-botfather-token-0000000000
SPARK_TELEGRAM_BOT_ID=replace-this-with-the-bot-numeric-id
SPARK_TELEGRAM_ALLOWED_USER_ID=1
SPARK_TELEGRAM_WEBHOOK_PATH_SECRET=replace-this-path-secret-before-running-0001
SPARK_TELEGRAM_WEBHOOK_HEADER_SECRET=replace-this-header-secret-before-run-0001
SPARK_PUBLIC_BASE_URL=https://example.invalid
```

The application must reject these marker values outside tests and local development.

- [ ] **Step 5: Verify readiness against real dependencies**

Run:

```powershell
docker compose up -d postgres redis
Set-Location services/api
Copy-Item ../../.env.example .env
uv run pytest tests/test_config.py tests/test_readiness.py -v
uv run ruff check app tests
```

Expected: configuration unit tests pass; readiness integration test reports 200 with both containers healthy.

- [ ] **Step 6: Commit configuration and dependencies**

```powershell
git add .env.example compose.yml services/api/app services/api/tests
git commit -m "feat: add runtime configuration and readiness"
```

---

### Task 3: Create the Foundation Database Schema and Migration

**Files:**
- Create: `services/api/app/models.py`
- Create: `services/api/alembic.ini`
- Create: `services/api/alembic/env.py`
- Create: `services/api/alembic/script.py.mako`
- Create: `services/api/alembic/versions/*_foundation.py`
- Create: `services/api/tests/test_models.py`
- Create: `services/api/tests/test_migrations.py`

**Interfaces:**
- Produces: `User`, `Session`, `RawCapture`, `NormalizedContent`, `ProcessingJob`, `JobState`, `JobKind`, and `Base.metadata`.
- Consumes: the async database URL and sessionmaker from Task 2.

- [ ] **Step 1: Write failing persistence invariants**

```python
# services/api/tests/test_models.py
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import JobKind, ProcessingJob, RawCapture, User


async def test_duplicate_telegram_update_is_rejected(db_session):
    user = User(email="owner@example.com", password_hash="not-used-in-this-test")
    db_session.add(user)
    await db_session.flush()
    values = {
        "user_id": user.id,
        "telegram_bot_id": "bot-1",
        "telegram_update_id": 42,
        "telegram_chat_id": 7,
        "telegram_user_id": 9,
        "raw_update": {"update_id": 42},
        "original_text": "原始内容  不修改",
    }
    db_session.add_all([RawCapture(**values), RawCapture(**values)])

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_one_normalization_job_per_capture(db_session, user, raw_capture):
    first = ProcessingJob(
        user_id=user.id, raw_capture_id=raw_capture.id, kind=JobKind.NORMALIZE_TEXT
    )
    second = ProcessingJob(
        user_id=user.id, raw_capture_id=raw_capture.id, kind=JobKind.NORMALIZE_TEXT
    )
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        await db_session.commit()
```

- [ ] **Step 2: Run the model tests and observe failure**

Run: `uv run pytest tests/test_models.py -v`

Expected: import fails because `app.models` does not exist.

- [ ] **Step 3: Implement the model types and constraints**

```python
# services/api/app/models.py
import enum
import uuid
from datetime import datetime

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


class JobState(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    NEEDS_ATTENTION = "needs_attention"
    FAILED = "failed"


class JobKind(str, enum.Enum):
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
            "user_id", "telegram_bot_id", "telegram_update_id", name="uq_capture_telegram_update"
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
```

- [ ] **Step 4: Configure Alembic and generate the migration**

Run:

```powershell
Set-Location services/api
uv run alembic init alembic
uv run alembic revision --autogenerate -m "foundation"
uv run alembic upgrade head
```

Replace the generated `alembic/env.py` with:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
```

Verify the generated migration creates both PostgreSQL enums, five tables, foreign keys, and all named unique constraints. Keep the generated revision file in Git.

- [ ] **Step 5: Run migration and invariant tests**

Run:

```powershell
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest tests/test_migrations.py tests/test_models.py -v
uv run ruff check app tests alembic
```

Expected: migration round-trip succeeds; duplicate Telegram update and duplicate job tests pass.

- [ ] **Step 6: Commit the foundation schema**

```powershell
git add services/api/app/models.py services/api/alembic.ini services/api/alembic services/api/tests
git commit -m "feat: add foundation persistence schema"
```

---

### Task 4: Add Admin Bootstrap and Database-Backed Sessions

**Files:**
- Create: `services/api/app/auth/__init__.py`
- Create: `services/api/app/auth/security.py`
- Create: `services/api/app/auth/schemas.py`
- Create: `services/api/app/auth/service.py`
- Create: `services/api/app/auth/router.py`
- Create: `services/api/app/dependencies.py`
- Create: `services/api/app/cli.py`
- Modify: `services/api/app/main.py`
- Create: `services/api/tests/test_auth.py`
- Create: `services/api/tests/test_cli.py`

**Interfaces:**
- Produces: `hash_password`, `verify_password`, `create_session`, `require_user`, admin bootstrap CLI, login/logout/me routes.
- Consumes: `User`, `Session`, settings, and sessionmaker from Tasks 2–3.

- [ ] **Step 1: Write failing password and session tests**

```python
# services/api/tests/test_auth.py
from app.auth.security import hash_password, verify_password


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded) is True
    assert verify_password("wrong password", encoded) is False


async def test_login_sets_http_only_cookie(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "correct horse battery staple"},
    )

    assert response.status_code == 204
    assert "spark_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
```

- [ ] **Step 2: Run tests and observe missing auth modules**

Run: `uv run pytest tests/test_auth.py -v`

Expected: collection fails on `app.auth.security`.

- [ ] **Step 3: Implement password and opaque-session security**

```python
# services/api/app/auth/security.py
import hashlib
import secrets

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

Implement the core of `auth/service.py` as:

```python
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
```

Implement `require_user` in `dependencies.py`:

```python
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
```

Implement routes with these exact bodies/status codes:

```json
POST /api/auth/login {"email":"owner@example.com","password":"example-password-not-a-secret"} -> 204 + cookie
POST /api/auth/logout -> 204 + expired cookie
GET /api/auth/me -> 200 {"id":"<uuid>","email":"owner@example.com","timezone":"Asia/Shanghai"}
```

The cookie uses `httponly=True`, `samesite="lax"`, `secure=settings.session_cookie_secure`, and `max_age=settings.session_ttl_seconds`.

- [ ] **Step 4: Implement the one-account bootstrap command**

`python -m app.cli create-admin --email owner@example.com` must prompt twice with `getpass`, refuse a second user, store an Argon2 password hash, and print only the created email/id. It must also accept `--password-stdin` for noninteractive containers, reading exactly one line from stdin without echoing or logging it. Add CLI tests that monkeypatch `getpass.getpass`, verify stdin mode, and prove the second invocation exits nonzero.

- [ ] **Step 5: Run auth and CLI tests**

Run:

```powershell
uv run pytest tests/test_auth.py tests/test_cli.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

Expected: password, cookie, current-user, logout, expiry, and single-account bootstrap tests pass.

- [ ] **Step 6: Commit authentication**

```powershell
git add services/api/app services/api/tests
git commit -m "feat: add single-admin session authentication"
```

---

### Task 5: Persist Telegram Text Updates Idempotently

**Files:**
- Create: `services/api/app/telegram/__init__.py`
- Create: `services/api/app/telegram/schemas.py`
- Create: `services/api/app/telegram/client.py`
- Create: `services/api/app/telegram/router.py`
- Create: `services/api/app/captures/__init__.py`
- Create: `services/api/app/captures/service.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/cli.py`
- Create: `services/api/tests/test_telegram_webhook.py`
- Create: `services/api/tests/test_telegram_client.py`

**Interfaces:**
- Produces: `TelegramUpdate`, `TelegramClient`, `create_capture_from_update`, authenticated Webhook, Webhook registration CLI.
- Consumes: models, settings, current single admin, and sessionmaker from earlier tasks.

- [ ] **Step 1: Write failing authentication and idempotency tests**

```python
# services/api/tests/test_telegram_webhook.py
from sqlalchemy import func, select

from app.models import ProcessingJob, RawCapture

TEST_PATH_SECRET = "test-path-secret-that-is-not-real-0001"

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


async def test_webhook_rejects_wrong_header(client):
    response = client.post(f"/api/telegram/webhook/{TEST_PATH_SECRET}", json=TELEGRAM_UPDATE)

    assert response.status_code == 404


async def test_duplicate_update_creates_one_capture_and_job(client, db_session, telegram_headers):
    first = client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}", json=TELEGRAM_UPDATE, headers=telegram_headers
    )
    second = client.post(
        f"/api/telegram/webhook/{TEST_PATH_SECRET}", json=TELEGRAM_UPDATE, headers=telegram_headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    capture_count = await db_session.scalar(select(func.count()).select_from(RawCapture))
    job_count = await db_session.scalar(select(func.count()).select_from(ProcessingJob))
    assert capture_count == 1
    assert job_count == 1
```

- [ ] **Step 2: Run focused tests and observe failure**

Run: `uv run pytest tests/test_telegram_webhook.py -v`

Expected: Webhook route returns 404 because the router is not registered.

- [ ] **Step 3: Implement strict Telegram schemas and the atomic capture service**

```python
# services/api/app/telegram/schemas.py
from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int
    is_bot: bool = False


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int
    type: str


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    message_id: int
    chat: TelegramChat
    from_: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    update_id: int
    message: TelegramMessage | None = None
```

Implement `create_capture_from_update` with PostgreSQL `insert(RawCapture).on_conflict_do_nothing(constraint="uq_capture_telegram_update").returning(RawCapture.id)`, then select the existing capture by the three unique-key columns when no id is returned. Insert a `JobKind.NORMALIZE_TEXT` job only for a newly created text capture. Preserve `update.model_dump(by_alias=True)` and `message.text` exactly.

- [ ] **Step 4: Implement secret and sender checks before persistence**

The router must:

1. compare the URL secret and `X-Telegram-Bot-Api-Secret-Token` using `secrets.compare_digest`;
2. return 404 for either mismatch;
3. load the only admin account;
4. accept only the configured private Telegram user id;
5. persist unsupported/non-text updates as raw captures without a normalization job;
6. commit before attempting Redis publication or `sendMessage`;
7. return `{"ok": true, "created": <bool>, "capture_id": "<uuid>"}`.

Implement `TelegramClient` with `httpx.AsyncClient` and methods `get_me`, `set_webhook`, and `send_message`. The token may appear only in the request URL constructed inside the client and must be scrubbed from raised/logged messages. Add `python -m app.cli register-webhook`, which calls `setWebhook` with the public URL, header secret, and `allowed_updates=["message"]`.

- [ ] **Step 5: Verify Telegram behavior**

Run:

```powershell
uv run pytest tests/test_telegram_webhook.py tests/test_telegram_client.py -v
uv run ruff check app tests
```

Expected: wrong secret/user tests reject without writes; duplicate delivery creates one capture/job; the client sends the expected Telegram API payload with no secret in captured logs.

- [ ] **Step 6: Commit Telegram capture**

```powershell
git add services/api/app services/api/tests
git commit -m "feat: capture Telegram text updates idempotently"
```

---

### Task 6: Dispatch and Process Text Normalization Jobs

**Files:**
- Create: `services/api/app/jobs/__init__.py`
- Create: `services/api/app/jobs/dispatcher.py`
- Create: `services/api/app/jobs/worker.py`
- Modify: `services/api/app/telegram/router.py`
- Create: `services/api/tests/test_dispatcher.py`
- Create: `services/api/tests/test_worker.py`

**Interfaces:**
- Produces: `publish_job(redis, job_id)`, `recover_queued_jobs(session, redis)`, `process_job(session, job_id)`, `python -m app.jobs.worker`.
- Consumes: `ProcessingJob`, `RawCapture`, `NormalizedContent`, Redis, and the post-commit job id.

- [ ] **Step 1: Write failing normalization and idempotency tests**

```python
# services/api/tests/test_worker.py
from sqlalchemy import func, select

from app.jobs.worker import normalize_text, process_job
from app.models import JobState, NormalizedContent


def test_normalize_text_changes_line_endings_but_preserves_spacing():
    assert normalize_text("  第一条\r\n保留  空格  ") == "  第一条\n保留  空格  "


async def test_processing_same_job_twice_creates_one_derivation(db_session, queued_text_job):
    first = await process_job(db_session, queued_text_job.id)
    second = await process_job(db_session, queued_text_job.id)

    assert first.state == JobState.PROCESSED
    assert second.state == JobState.PROCESSED
    count = await db_session.scalar(
        select(func.count())
        .select_from(NormalizedContent)
        .where(NormalizedContent.raw_capture_id == queued_text_job.raw_capture_id)
    )
    assert count == 1
```

- [ ] **Step 2: Run focused tests and observe failure**

Run: `uv run pytest tests/test_worker.py -v`

Expected: import fails because `app.jobs.worker` does not exist.

- [ ] **Step 3: Implement Redis Stream publication and recovery**

```python
# services/api/app/jobs/dispatcher.py
import uuid

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobState, ProcessingJob

STREAM = "spark:jobs"


async def publish_job(redis: Redis, job_id: uuid.UUID) -> None:
    await redis.xadd(STREAM, {"job_id": str(job_id)})


async def recover_queued_jobs(session: AsyncSession, redis: Redis, limit: int = 100) -> int:
    ids = list(
        await session.scalars(
            select(ProcessingJob.id)
            .where(ProcessingJob.state == JobState.QUEUED)
            .order_by(ProcessingJob.created_at)
            .limit(limit)
        )
    )
    for job_id in ids:
        await publish_job(redis, job_id)
    return len(ids)
```

After the Webhook transaction commits, attempt `publish_job`. Catch Redis exceptions, log only the job id/error class, and still return 200 because `recover_queued_jobs` can republish the database row.

- [ ] **Step 4: Implement transactional job claiming and derivation**

`process_job` must lock the job with this query:

```python
job = await session.scalar(
    select(ProcessingJob)
    .where(ProcessingJob.id == job_id)
    .with_for_update(skip_locked=True)
)
```

Use that query in this implementation:

```python
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobState, NormalizedContent, ProcessingJob, RawCapture


def normalize_text(value: str) -> str:
    line_normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", line_normalized)


async def process_job(session: AsyncSession, job_id: uuid.UUID) -> ProcessingJob:
    job = await session.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.id == job_id)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        raise LookupError(f"processing job not found: {job_id}")
    if job.state == JobState.PROCESSED:
        return job

    job.state = JobState.PROCESSING
    job.attempts += 1
    raw = await session.get(RawCapture, job.raw_capture_id)
    if raw is None or raw.original_text is None:
        job.state = JobState.FAILED
        job.last_error_code = "unsupported_content"
        job.last_error_message = "Text normalization requires original_text"
        await session.commit()
        return job

    statement = insert(NormalizedContent).values(
        user_id=job.user_id,
        raw_capture_id=raw.id,
        normalized_text=normalize_text(raw.original_text),
        language=None,
    ).on_conflict_do_nothing(constraint="uq_normalized_capture")
    await session.execute(statement)
    job.state = JobState.PROCESSED
    job.last_error_code = None
    job.last_error_message = None
    await session.commit()
    return job
```

Missing/non-text raw content marks the job `FAILED` with code `unsupported_content`.

The worker entrypoint must create the Redis consumer group once, call `recover_queued_jobs` on startup and every 30 seconds, consume job ids, call `process_job`, acknowledge the stream message only after the database commit, and increment `attempts` on a caught processing failure.

- [ ] **Step 5: Run worker tests with PostgreSQL and Redis**

Run:

```powershell
uv run pytest tests/test_dispatcher.py tests/test_worker.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

Expected: stream message includes the job id; recovery republishes queued rows; duplicate processing creates one derived row; raw text remains byte-for-byte unchanged.

- [ ] **Step 6: Commit asynchronous processing**

```powershell
git add services/api/app services/api/tests
git commit -m "feat: process text captures asynchronously"
```

---

### Task 7: Add the Authenticated Capture Feed Dashboard

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `pnpm-lock.yaml`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Modify: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/login/page.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Create: `apps/web/src/components/capture-feed.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/components/capture-feed.test.tsx`
- Create: `services/api/app/captures/router.py`
- Modify: `services/api/app/main.py`
- Create: `services/api/tests/test_capture_feed.py`

**Interfaces:**
- Produces: authenticated paginated capture API, login page, protected feed, capture cards.
- Consumes: `require_user`, `RawCapture`, `NormalizedContent`, and auth endpoints.

- [ ] **Step 1: Write the failing capture-feed API test**

```python
# services/api/tests/test_capture_feed.py
async def test_capture_feed_is_user_scoped(authenticated_client, raw_capture, normalized_content):
    response = authenticated_client.get("/api/captures?limit=50")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id"] == str(raw_capture.id)
    assert body["items"][0]["original_text"] == raw_capture.original_text
    assert body["items"][0]["normalized_text"] == normalized_content.normalized_text
    assert body["items"][0]["processing_state"] == "processed"
```

- [ ] **Step 2: Implement cursor pagination and the API response**

Create `captures/router.py` with a maximum `limit` of 100. Order by `(created_at DESC, id DESC)`, filter by `current_user.id`, outer-join normalized content and the normalization job, and return:

```json
{
  "items": [
    {
      "id": "uuid",
      "received_at": "2026-07-14T12:00:00Z",
      "original_text": "原始内容",
      "normalized_text": "原始内容",
      "processing_state": "processed",
      "source": "telegram"
    }
  ],
  "next_cursor": null
}
```

Run `uv run pytest tests/test_capture_feed.py -v`; expected: pass.

- [ ] **Step 3: Scaffold the pinned Next.js workspace**

Run:

```powershell
corepack enable
corepack prepare pnpm@11.13.0 --activate
pnpm create next-app@16.2.10 apps/web --ts --eslint --app --src-dir --use-pnpm --import-alias "@/*" --no-tailwind
```

Create root files:

`package.json`:

```json
{
  "name": "spark-memory",
  "private": true,
  "packageManager": "pnpm@11.13.0",
  "scripts": {
    "web:dev": "pnpm --dir apps/web dev",
    "web:check": "pnpm --dir apps/web check"
  }
}
```

```yaml
# pnpm-workspace.yaml
packages:
  - "apps/*"
```

Pin `next=16.2.10`, `react=19.2.7`, `react-dom=19.2.7`, `typescript=7.0.2`, `zod=4.4.3`, `vitest=4.1.10`, `@testing-library/react=16.3.2`, and `@testing-library/jest-dom=6.9.1`. Add `check` as `eslint . && tsc --noEmit && vitest run`.

- [ ] **Step 4: Write a failing component test**

```tsx
// apps/web/src/components/capture-feed.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaptureFeed } from "./capture-feed";

describe("CaptureFeed", () => {
  it("shows source, text, and processing state", () => {
    render(
      <CaptureFeed
        items={[{
          id: "018f0000-0000-7000-8000-000000000001",
          receivedAt: "2026-07-14T12:00:00Z",
          originalText: "第一条 Spark",
          normalizedText: "第一条 Spark",
          processingState: "processed",
          source: "telegram",
        }]}
      />,
    );

    expect(screen.getByText("第一条 Spark")).toBeInTheDocument();
    expect(screen.getByText("已处理")).toBeInTheDocument();
    expect(screen.getByText("Telegram")).toBeInTheDocument();
  });
});
```

Run: `pnpm --dir apps/web vitest run src/components/capture-feed.test.tsx`

Expected: failure because `CaptureFeed` does not exist.

- [ ] **Step 5: Implement typed API schemas, login, and protected feed**

`apps/web/src/lib/api.ts` must validate API data with Zod and expose `login(email, password)`, `getCurrentUser(cookieHeader)`, and `getCaptures(cookieHeader)`. `next.config.ts` must rewrite `/api/:path*` to `API_PROXY_TARGET` without exposing an internal hostname to the browser.

`/login` posts JSON to `/api/auth/login`, shows invalid credentials without logging the password, and redirects to `/`. `/` checks `/api/auth/me`; a 401 redirects to `/login`; a success renders the Agent Briefing header plus `CaptureFeed`.

Implement `CaptureFeed` as:

```tsx
export type CaptureItem = {
  id: string;
  receivedAt: string;
  originalText: string | null;
  normalizedText: string | null;
  processingState: "queued" | "processing" | "processed" | "needs_attention" | "failed";
  source: "telegram";
};

const stateLabels: Record<CaptureItem["processingState"], string> = {
  queued: "待处理",
  processing: "处理中",
  processed: "已处理",
  needs_attention: "需要处理",
  failed: "失败",
};

export function CaptureFeed({ items }: { items: CaptureItem[] }) {
  if (items.length === 0) {
    return <p className="empty-state">还没有 Spark。直接给 Telegram Bot 发一条消息吧。</p>;
  }

  return (
    <ol className="capture-feed">
      {items.map((item) => (
        <li className="capture-card" key={item.id}>
          <div className="capture-meta">
            <span>Telegram</span>
            <time dateTime={item.receivedAt}>
              {new Intl.DateTimeFormat("zh-CN", {
                dateStyle: "medium",
                timeStyle: "short",
                timeZone: "Asia/Shanghai",
              }).format(new Date(item.receivedAt))}
            </time>
            <span>{stateLabels[item.processingState]}</span>
          </div>
          <p>{item.originalText ?? "非文字内容"}</p>
          {item.normalizedText !== null && item.normalizedText !== item.originalText ? (
            <p className="normalized-text">{item.normalizedText}</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
```

Use `globals.css` with a warm neutral palette, readable 16px base type, visible focus states, no gradients, and a responsive single-column layout below 760px.

- [ ] **Step 6: Run web and API checks**

Run:

```powershell
pnpm --dir apps/web check
Set-Location services/api
uv run pytest tests/test_capture_feed.py -v
uv run ruff check app tests
```

Expected: component/API tests pass; ESLint and TypeScript exit 0.

- [ ] **Step 7: Commit the first Dashboard**

```powershell
git add package.json pnpm-workspace.yaml pnpm-lock.yaml apps/web services/api/app services/api/tests
git commit -m "feat: show captured Sparks in Dashboard"
```

---

### Task 8: Containerize the Vertical Slice and Prove It End to End

**Files:**
- Create: `services/api/Dockerfile`
- Create: `apps/web/Dockerfile`
- Modify: `compose.yml`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/e2e/text-capture.spec.ts`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Produces: `docker compose up --build` runnable system and CI validation.
- Consumes: all Task 1–7 interfaces.

- [ ] **Step 1: Write the failing Playwright scenario**

```ts
// apps/web/e2e/text-capture.spec.ts
import { expect, test } from "@playwright/test";

test("admin sees a Telegram text capture", async ({ page, request }) => {
  const webhook = await request.post(
    `${process.env.E2E_API_URL}/api/telegram/webhook/${process.env.E2E_WEBHOOK_PATH}`,
    {
      headers: {
        "X-Telegram-Bot-Api-Secret-Token": process.env.E2E_WEBHOOK_HEADER!,
      },
      data: {
        update_id: 9001,
        message: {
          message_id: 1,
          date: 1784020000,
          chat: { id: 7788, type: "private" },
          from: { id: 7788, is_bot: false, first_name: "Owner" },
          text: "来自 Telegram 的第一条 Spark",
        },
      },
    },
  );
  expect(webhook.ok()).toBeTruthy();

  await page.goto("/login");
  await page.getByLabel("邮箱").fill(process.env.E2E_ADMIN_EMAIL!);
  await page.getByLabel("密码").fill(process.env.E2E_ADMIN_PASSWORD!);
  await page.getByRole("button", { name: "登录" }).click();

  await expect.poll(async () => {
    await page.reload();
    return page.getByText("来自 Telegram 的第一条 Spark").isVisible();
  }).toBe(true);
  await expect(page.getByText("已处理")).toBeVisible();
});
```

- [ ] **Step 2: Run Playwright before container wiring and observe failure**

Run: `pnpm --dir apps/web exec playwright test e2e/text-capture.spec.ts`

Expected: fails because the composed application is not running.

- [ ] **Step 3: Add production containers and composed services**

The API Dockerfile uses `python:3.13-slim`, copies `uv` from the official `ghcr.io/astral-sh/uv` image, installs from `uv.lock --frozen --no-dev`, and runs Uvicorn as a non-root user. The worker uses the same image with command `python -m app.jobs.worker`.

The web Dockerfile uses `node:24-alpine`, `corepack`, `pnpm install --frozen-lockfile`, `next build`, and a non-root Next.js standalone runner.

Extend `compose.yml` with:

- `api`, depending on healthy PostgreSQL/Redis and running `alembic upgrade head` before Uvicorn;
- `worker`, depending on the same services;
- `web`, depending on API readiness and setting `API_PROXY_TARGET=http://api:8000`;
- named volumes only for PostgreSQL and Redis;
- secrets supplied from `.env`, never committed.

- [ ] **Step 4: Add CI with service containers**

```yaml
# .github/workflows/ci.yml
name: ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:0.8.2-pg18-bookworm
        env:
          POSTGRES_DB: spark_test
          POSTGRES_USER: spark
          POSTGRES_PASSWORD: spark
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U spark -d spark_test"
          --health-interval 3s --health-timeout 3s --health-retries 20
      redis:
        image: redis:8-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 3s --health-timeout 3s --health-retries 20
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.13"
      - run: uv sync --locked --all-groups
        working-directory: services/api
      - run: uv run alembic upgrade head
        working-directory: services/api
      - run: uv run ruff check app tests alembic
        working-directory: services/api
      - run: uv run ruff format --check app tests alembic
        working-directory: services/api
      - run: uv run pytest -v
        working-directory: services/api

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 11.13.0
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm --dir apps/web check
      - run: pnpm --dir apps/web build
```

- [ ] **Step 5: Run the full milestone verification**

Run:

```powershell
docker compose down
docker compose up -d --build
$env:E2E_ADMIN_PASSWORD | docker compose exec -T api python -m app.cli create-admin --email owner@example.com --password-stdin
pnpm --dir apps/web exec playwright install chromium
pnpm --dir apps/web exec playwright test e2e/text-capture.spec.ts
Set-Location services/api
uv run pytest -v
uv run ruff check app tests alembic
Set-Location ../..
pnpm --dir apps/web check
pnpm --dir apps/web build
```

Expected: Playwright proves the Telegram-to-Dashboard flow; all Python and web checks pass; builds exit 0.

- [ ] **Step 6: Update README status accurately**

Change README from “application code has not started” to “Milestone 1 runnable text capture slice.” Add exact local startup, admin bootstrap, Webhook registration, test, and shutdown commands. State clearly that Settings/BYOK, LLM organization, multimedia, Running-up, and Tavily are not in Milestone 1.

- [ ] **Step 7: Commit the runnable vertical slice**

```powershell
git add compose.yml services/api/Dockerfile apps/web/Dockerfile apps/web/playwright.config.ts apps/web/e2e .github/workflows/ci.yml README.md
git commit -m "feat: deliver Telegram text capture vertical slice"
```

---

## Plan Self-Review Checklist

Before declaring this milestone complete during execution, verify:

- [ ] All raw Telegram fields remain unchanged after worker processing.
- [ ] Duplicate Telegram delivery creates exactly one raw capture and one normalization job.
- [ ] Wrong URL secret, header secret, or Telegram user creates no row.
- [ ] PostgreSQL contains the job before any Redis or Telegram network call.
- [ ] A Redis outage does not turn a persisted capture into an HTTP error.
- [ ] Worker restart and queued-job recovery complete the derivation once.
- [ ] Unauthenticated Dashboard/API requests return 401 or redirect to login.
- [ ] Capture feed queries include `user_id` filters.
- [ ] Cookies are HTTP-only and production configuration enables `Secure`.
- [ ] Logs and test output contain no Bot Token, password, cookie, or Webhook secret.
- [ ] `uv.lock`, `pnpm-lock.yaml`, migration, and CI workflow are committed.
- [ ] Docker Compose, API tests/lint, web tests/type/lint/build, and Playwright all pass from a clean checkout.
