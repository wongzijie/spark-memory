# Spark Memory MVP 中英对照实施指南 / Bilingual Implementation Guide

本文把 Spark Memory 的七阶段 MVP 路线图与第一阶段实施计划整理成逐段中英对照版本。中文用于快速理解产品目标与工程决策，英文用于保持接口、任务名称和项目协作语义的一致性。

This guide presents the seven-milestone Spark Memory MVP roadmap and the Milestone 1 implementation plan in paired Chinese and English. Chinese supports fast product review, while English keeps interfaces, task names, and engineering collaboration consistent.

代码、配置和命令的语法在两种语言中相同，因此只保留一份。每个测试和实现片段的完整内容位于英文详细计划中，本指南完整对应其任务顺序、接口、验收证据和提交边界。

Code, configuration, and command syntax are language-neutral, so each appears once. The complete test and implementation snippets remain in the detailed English plan; this guide fully mirrors its task order, interfaces, acceptance evidence, and commit boundaries.

## 配套文档 / Companion Documents

- [产品与架构设计 / Product and architecture design](../specs/2026-07-14-spark-memory-mvp-design.md)
- [七阶段路线图 / Seven-milestone roadmap](2026-07-14-spark-memory-mvp-roadmap.md)
- [第一阶段完整代码级计划 / Milestone 1 code-level plan](2026-07-14-spark-memory-foundation-text-capture.md)

## 一、MVP 路线图 / MVP Roadmap

### 阶段 1：基础设施与 Telegram 文本采集 / Milestone 1: Foundation and Telegram Text Capture

**中文目标：** 交付一个可运行的单账户垂直切片。Telegram 文本消息通过认证后进入系统，原始更新被不可变地保存，Redis 驱动后台处理，管理员登录 Dashboard 后可以看到内容和处理状态。

**English goal:** Deliver a runnable single-account vertical slice. An authenticated Telegram text message enters the system, the raw update is stored immutably, Redis drives background processing, and the logged-in admin can see the content and processing state in the Dashboard.

**退出证据 / Exit evidence:**

- PostgreSQL 与 Redis 可通过 Docker Compose 启动。 / PostgreSQL and Redis start through Docker Compose.
- 初始管理员可以完成登录和退出。 / The bootstrapped admin can log in and log out.
- Telegram Webhook 同时校验路径密钥、Header 密钥和发送者身份。 / The Telegram Webhook validates the path secret, header secret, and sender identity.
- 重复投递不会产生重复原始笔记或后台任务。 / Duplicate delivery does not create duplicate raw captures or background jobs.
- Worker 生成标准化派生内容，但不修改原始输入。 / The worker creates normalized derived content without modifying the raw input.
- Dashboard 展示消息、来源时间和处理状态。 / The Dashboard displays the message, source time, and processing state.

### 阶段 2：Settings、凭据保险库与 Bot 接入 / Milestone 2: Settings, Credential Vault, and Bot Onboarding

**中文目标：** 保留并实现 Settings 入口，让用户在 Dashboard 内自行管理 Telegram Bot Token、云端模型 API Key 和 Tavily Key，不再依赖开发者手工修改 `.env`。

**English goal:** Implement the reserved Settings entry so the user can manage the Telegram Bot token, cloud-model API key, and Tavily key inside the Dashboard without developer-managed `.env` edits.

**退出证据 / Exit evidence:**

- 凭据使用 AES-256-GCM 加密存储，界面只显示掩码。 / Credentials are stored with AES-256-GCM encryption and only masked values are shown in the UI.
- 保存的密钥不会返回浏览器，也不会出现在日志中。 / Saved secrets are never returned to the browser or written to logs.
- Telegram `getMe` 校验成功后自动注册 Webhook。 / A successful Telegram `getMe` validation triggers automatic Webhook registration.
- 用户与 Bot 完成一次性绑定，并可安全轮换或删除凭据。 / The user and Bot complete one-time binding, with safe credential rotation and deletion.
- 删除凭据后，依赖该凭据的任务进入暂停状态并给出原因。 / Deleting a credential pauses dependent jobs and records the reason.

### 阶段 3：记忆工作台与记忆本 / Milestone 3: Memory Workspace and Memory Books

**中文目标：** 把不可变采集内容转化为可管理、可版本化的正式笔记，并允许一条笔记同时属于多个记忆本，从根本上避免“记录前必须先分类”。

**English goal:** Turn immutable captures into manageable, versioned canonical notes and allow one note to belong to multiple memory books, removing the need to classify before capture.

**退出证据 / Exit evidence:**

- 支持记忆本的新建、重命名、归档、恢复与删除。 / Memory books support create, rename, archive, restore, and delete operations.
- 笔记与记忆本是多对多关系。 / Notes and memory books use a many-to-many relationship.
- 三栏工作台支持检索、筛选、详情、来源和版本时间线。 / The three-column workspace supports search, filters, detail, sources, and version timelines.
- 用户可合并、拆分、编辑、撤销、移入回收站并恢复笔记。 / Users can merge, split, edit, undo, recycle, and restore notes.
- 每次变更都保留来源与版本，不覆盖原始采集。 / Every change preserves provenance and versions without overwriting raw captures.

### 阶段 4：知识编译器与持续生长的记忆图谱 / Milestone 4: Knowledge Compiler and Living Memory Graph

**中文目标：** 参考复利式个人知识库逻辑，让 Agent 将散乱输入编译为持续更新的页面、主张和关系，而不是把每条输入孤立地总结成一次性结果。

**English goal:** Follow a compounding personal-knowledge-base model in which the Agent compiles scattered inputs into continuously updated pages, claims, and relationships instead of producing isolated one-off summaries.

**退出证据 / Exit evidence:**

- 模型适配层支持可替换的云端大模型供应商。 / The model adapter supports replaceable cloud-model providers.
- Agent Schema 具有明确版本，结构化 ChangeSet 可验证。 / Agent Schema versions are explicit and structured ChangeSets are validated.
- 检索与重排只提供相关上下文，避免把整个记忆库塞进提示词。 / Retrieval and reranking provide only relevant context instead of placing the whole memory store into a prompt.
- 页面、主张、关系和来源具有明确的数据模型。 / Pages, claims, edges, and sources have explicit data models.
- 所有 Agent 变更先验证来源，再在事务中应用，并可逆转。 / Every Agent mutation validates provenance before transactional application and remains reversible.
- 矛盾、过期信息与孤立节点由每日或每周 lint 暴露。 / Daily or weekly lint exposes contradictions, stale information, and orphaned nodes.

### 阶段 5：实时与多模态采集 / Milestone 5: Real-Time and Multimodal Capture

**中文目标：** 让语音、手写图片、普通图片、文档和视频进入同一套不可变来源与知识编译管线，并支持一段发散思考作为一个实时会话整体处理。

**English goal:** Route voice, handwritten images, ordinary images, documents, and video through the same immutable-source and Knowledge Compiler pipeline, while treating a burst of divergent thinking as one real-time session.

**退出证据 / Exit evidence:**

- 语音完成转写，图片和手写完成 OCR 或视觉理解。 / Voice is transcribed, while images and handwriting receive OCR or vision processing.
- 文档完成结构化提取，视频完成音轨与关键帧处理。 / Documents receive structured extraction, while video receives audio-track and keyframe processing.
- 原始媒体进入对象存储，并遵守类型、大小和时长限制。 / Original media enters object storage and obeys type, size, and duration limits.
- 连续消息自动归入实时会话并生成滚动摘要。 / Consecutive messages are grouped into a real-time session with a rolling summary.
- 空闲超时或 `/close` 只触发一次最终编译。 / Idle timeout or `/close` triggers final compilation exactly once.
- 用户可以合并或拆分识别错误的会话。 / Users can merge or split incorrectly detected sessions.

### 阶段 6：定时任务、Running-up 与 Tavily / Milestone 6: Scheduled Tasks and Running-Up with Tavily

**中文目标：** 同时支持确定性提醒与 Agent 驱动的智能跟进。Running-up 不是普通定时器，而是能够搜索网络、评估新证据、向用户提问并决定下一步时间的状态机。

**English goal:** Support both deterministic reminders and Agent-driven intelligent follow-up. Running-up is not a simple timer; it is a state machine that can search the web, evaluate new evidence, ask the user, and choose its next check time.

**退出证据 / Exit evidence:**

- 自然语言时间可以转换为一次性或重复规则。 / Natural-language time becomes one-time or recurring rules.
- 调度器重启后可恢复任务，并保证同一触发点只执行一次。 / The scheduler recovers after restart and executes each trigger point once.
- Running-up 具有持久化状态、完成条件、重试和预算。 / Running-up has durable states, completion conditions, retries, and budgets.
- Tavily 搜索结果保留查询、链接、抓取时间与引用关系。 / Tavily results preserve query, link, retrieval time, and citation relationships.
- 搜索结果去重，成本和频率受控。 / Search results are deduplicated, with controlled cost and frequency.
- Agent 可更新证据、请求用户补充信息，或安排下一次检查。 / The Agent can update evidence, request user input, or schedule the next check.
- 跟进结果通过 Telegram 通知，并写回相关笔记与时间线。 / Follow-up results are notified through Telegram and written back to the related note and timeline.

### 阶段 7：运行加固与 MVP 发布 / Milestone 7: Operational Hardening and MVP Release

**中文目标：** 把功能正确的系统变成可公开部署、可监控、可恢复的 MVP，并用故障演练证明数据不会因常见事故丢失。

**English goal:** Turn a functionally correct system into a publicly deployable, observable, and recoverable MVP, with failure drills proving that common incidents do not lose data.

**退出证据 / Exit evidence:**

- 云端部署启用 HTTPS、速率限制与成本上限。 / Cloud deployment enables HTTPS, rate limits, and cost caps.
- 日志为结构化格式，关键管线具有指标和告警。 / Logs are structured, and critical pipelines have metrics and alerts.
- 回收站保留 30 天。 / Recycle-bin content is retained for 30 days.
- 备份保留七份日备份和四份周备份。 / Backups retain seven daily copies and four weekly copies.
- 已执行数据库与对象存储的恢复演练。 / Restore drills cover both the database and object storage.
- 设计文档中的全部 MVP 验收标准均在部署环境通过。 / Every MVP acceptance criterion in the design document passes in the deployed environment.

## 二、第一阶段详细实施计划 / Milestone 1 Detailed Implementation Plan

### 技术基线 / Technical Baseline

| 层级 / Layer | 固定选择 / Pinned choice |
| --- | --- |
| API 与 Worker / API and worker | Python 3.13, FastAPI 0.139.0, Pydantic 2.13.4, SQLAlchemy 2.0.51, Alembic 1.18.5, psycopg 3.3.4, redis-py 8.0.1 |
| 数据层 / Data layer | PostgreSQL 18, pgvector 0.8.2, Redis 8 |
| Dashboard | Node.js 24, pnpm 11.13.0, Next.js 16.2.10, React 19.2.7, TypeScript 7.0.2 |
| 测试 / Testing | pytest, Vitest 4.1.10, Playwright 1.61.1 |
| 本地编排 / Local orchestration | Docker Compose |

### 全局工程约束 / Global Engineering Constraints

- PostgreSQL 是事实来源；Redis Stream 只负责唤醒 Worker。数据库中的排队任务必须能在消息发布失败后恢复。 / PostgreSQL is the source of truth; Redis Streams only wake workers. Queued database jobs must be recoverable after publication failure.
- 原始 Telegram Update 与原始文本不可修改。所有清洗结果写入独立派生记录。 / Raw Telegram updates and original text are immutable. Every cleaned result is written as a separate derivation.
- 浏览器仅使用安全、HTTP-only 的不透明会话 Cookie。 / The browser uses only a secure, HTTP-only opaque session cookie.
- Next.js 代理 `/api` 到 FastAPI，浏览器保持同源访问。 / Next.js proxies `/api` to FastAPI so the browser remains on one origin.
- 本阶段只实现单管理员与 Telegram 文本入口。Settings、LLM 整理、多模态、Running-up 和 Tavily 保留在后续阶段。 / This milestone implements one admin and Telegram text capture only. Settings, LLM organization, multimodal capture, Running-up, and Tavily remain in later milestones.
- 每个任务遵循“先写失败测试、确认失败、最小实现、重新验证、独立提交”的顺序。 / Every task follows the order: write a failing test, confirm failure, implement minimally, verify again, and commit independently.

### 任务 1：创建 FastAPI 项目与存活契约 / Task 1: Create the FastAPI Project and Liveness Contract

**目标 / Goal:** 建立最小可运行 API 项目，并锁定应用工厂与存活检查接口。 / Establish the smallest runnable API project and lock the application factory and liveness interface.

**文件范围 / File scope:** `.python-version`, `services/api/pyproject.toml`, `services/api/app/main.py`, `services/api/app/health/router.py`, `services/api/tests/conftest.py`, `services/api/tests/test_health.py`，以及相应包初始化文件。 / The listed project, application, health-route, fixture, test, and package initialization files.

**接口 / Interfaces:**

- 产出 / Produces: `create_app() -> FastAPI`
- 产出 / Produces: `GET /health/live -> {"status": "ok"}`
- 依赖 / Consumes: 无 / None

**执行步骤 / Execution steps:**

1. 先写 `/health/live` 的失败测试与 `TestClient` fixture。 / Write the failing `/health/live` test and `TestClient` fixture first.
2. 创建并锁定 Python 3.13 项目依赖，然后确认测试因 `app.main` 不存在而失败。 / Create and lock the Python 3.13 project dependencies, then confirm the test fails because `app.main` does not exist.
3. 实现 `create_app()` 和 health router，只满足当前契约。 / Implement `create_app()` and the health router, satisfying only the current contract.
4. 运行聚焦测试、Ruff 静态检查和格式检查。 / Run the focused test, Ruff lint, and format checks.
5. 以独立提交保存 API 基础。 / Save the API foundation in an independent commit.

**验证 / Verification:**

```powershell
Set-Location services/api
uv run pytest tests/test_health.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

**预期结果 / Expected result:** 存活测试通过，Ruff 以状态码 0 退出。 / The liveness test passes and Ruff exits with status 0.

**提交 / Commit:** `feat: scaffold Spark Memory API`

### 任务 2：加入校验配置与服务就绪检查 / Task 2: Add Validated Configuration and Service Readiness

**目标 / Goal:** 通过强类型配置阻止弱密钥和错误地址进入运行环境，并使用真实 PostgreSQL 与 Redis 验证服务就绪。 / Use strongly validated settings to reject weak secrets and invalid addresses, then verify readiness against real PostgreSQL and Redis services.

**文件范围 / File scope:** `.env.example`, `compose.yml`, `services/api/app/config.py`, `services/api/app/db.py`, `services/api/app/redis.py`, health 与 app factory 修改，以及配置和 readiness 测试。 / Environment example, Compose services, configuration, database and Redis factories, health and app-factory updates, plus configuration and readiness tests.

**接口 / Interfaces:**

- 产出 / Produces: `get_settings() -> Settings`
- 产出 / Produces: `create_engine_and_sessionmaker(settings)`
- 产出 / Produces: `create_redis(settings)`
- 产出 / Produces: `GET /health/ready`
- 依赖 / Consumes: 任务 1 的 `create_app()` / `create_app()` from Task 1

**执行步骤 / Execution steps:**

1. 编写配置失败测试，覆盖弱密钥、默认时区与 URL 校验。 / Write failing configuration tests covering weak secrets, the default timezone, and URL validation.
2. 运行聚焦测试并确认配置模块缺失。 / Run focused tests and confirm the configuration module is missing.
3. 实现 Pydantic Settings、异步数据库连接工厂和 Redis 客户端工厂。 / Implement Pydantic Settings, the async database connection factory, and the Redis client factory.
4. 在 Compose 中加入固定版本的 PostgreSQL、pgvector 和 Redis 服务与健康检查。 / Add pinned PostgreSQL with pgvector and Redis services with health checks to Compose.
5. 对真实依赖运行配置与 readiness 测试。 / Run configuration and readiness tests against real dependencies.
6. 独立提交配置和依赖服务。 / Commit configuration and dependency services independently.

**验证 / Verification:**

```powershell
docker compose up -d postgres redis
Set-Location services/api
Copy-Item ../../.env.example .env
uv run pytest tests/test_config.py tests/test_readiness.py -v
uv run ruff check app tests
```

**预期结果 / Expected result:** 配置测试通过，两个依赖健康时 `/health/ready` 返回 200。 / Configuration tests pass and `/health/ready` returns 200 when both dependencies are healthy.

**提交 / Commit:** `feat: add runtime configuration and readiness`

### 任务 3：建立基础数据库模型与迁移 / Task 3: Create the Foundation Database Schema and Migration

**目标 / Goal:** 建立不可变采集、派生内容和可恢复任务的最小持久化模型，并用数据库约束保证幂等性。 / Establish the minimum persistence model for immutable captures, derived content, and recoverable jobs, using database constraints to guarantee idempotency.

**文件范围 / File scope:** `services/api/app/models.py`, Alembic 配置、环境、模板和 foundation migration，以及 model 与 migration 测试。 / SQLAlchemy models, Alembic configuration, environment, template and foundation migration, plus model and migration tests.

**接口 / Interfaces:**

- 产出 / Produces: `User`, `Session`, `RawCapture`, `NormalizedContent`, `ProcessingJob`
- 产出 / Produces: `JobState`, `JobKind`, `Base.metadata`
- 依赖 / Consumes: 任务 2 的异步数据库 URL 与 sessionmaker / The async database URL and sessionmaker from Task 2

**执行步骤 / Execution steps:**

1. 编写失败的数据库不变量测试，覆盖 Telegram Update 去重和每条采集仅一个标准化任务。 / Write failing persistence-invariant tests covering Telegram Update deduplication and one normalization job per capture.
2. 运行测试并确认 model 模块缺失。 / Run the tests and confirm the model module is missing.
3. 实现 UUID 主键、枚举、时间戳、外键、唯一约束与必要索引。 / Implement UUID primary keys, enums, timestamps, foreign keys, unique constraints, and required indexes.
4. 配置 Alembic 并生成可审查的 foundation migration。 / Configure Alembic and generate a reviewable foundation migration.
5. 执行 downgrade、upgrade 和不变量测试。 / Run downgrade, upgrade, and persistence-invariant tests.
6. 独立提交基础 schema。 / Commit the foundation schema independently.

**验证 / Verification:**

```powershell
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest tests/test_migrations.py tests/test_models.py -v
uv run ruff check app tests alembic
```

**预期结果 / Expected result:** migration 往返成功，重复 Telegram Update 与重复任务被数据库拒绝。 / The migration round trip succeeds, and the database rejects duplicate Telegram updates and duplicate jobs.

**提交 / Commit:** `feat: add foundation persistence schema`

### 任务 4：加入管理员初始化与数据库会话 / Task 4: Add Admin Bootstrap and Database-Backed Sessions

**目标 / Goal:** 为 MVP 提供安全的单管理员初始化、登录、当前用户查询与退出流程。 / Provide secure single-admin bootstrap, login, current-user lookup, and logout flows for the MVP.

**文件范围 / File scope:** auth security、schemas、service、router、dependencies、CLI，`app.main` 修改，以及 auth 与 CLI 测试。 / Auth security, schemas, service, router, dependencies, CLI, app-factory updates, and auth and CLI tests.

**接口 / Interfaces:**

- 产出 / Produces: `hash_password`, `verify_password`, `create_session`, `require_user`
- 产出 / Produces: 管理员初始化 CLI、login、logout、me routes / Admin bootstrap CLI and login, logout, and me routes
- 依赖 / Consumes: 任务 2–3 的 `User`、`Session`、Settings 与 sessionmaker / `User`, `Session`, Settings, and sessionmaker from Tasks 2–3

**执行步骤 / Execution steps:**

1. 编写密码哈希、Cookie 属性、当前用户、退出与过期会话的失败测试。 / Write failing tests for password hashing, cookie attributes, current user, logout, and expired sessions.
2. 运行测试并确认 auth 模块缺失。 / Run the tests and confirm the auth modules are missing.
3. 实现密码哈希与不透明随机会话；数据库仅保存会话 Token 的哈希。 / Implement password hashing and opaque random sessions; store only the session-token hash in the database.
4. 实现只允许创建一个账户、支持从标准输入读取密码的 bootstrap 命令。 / Implement a bootstrap command that allows only one account and reads the password from standard input.
5. 运行 auth 与 CLI 测试和静态检查。 / Run auth and CLI tests and static checks.
6. 独立提交认证能力。 / Commit authentication independently.

**验证 / Verification:**

```powershell
uv run pytest tests/test_auth.py tests/test_cli.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

**预期结果 / Expected result:** 密码、Cookie、当前用户、退出、过期与单账户初始化测试全部通过。 / Password, cookie, current-user, logout, expiry, and single-account bootstrap tests all pass.

**提交 / Commit:** `feat: add single-admin session authentication`

### 任务 5：幂等保存 Telegram 文本更新 / Task 5: Persist Telegram Text Updates Idempotently

**目标 / Goal:** 在任何数据写入前认证 Telegram 请求和发送者，并将每个合法 Update 只保存一次。 / Authenticate the Telegram request and sender before any write, and persist each valid update exactly once.

**文件范围 / File scope:** Telegram schemas、client、router，capture service，app factory 与 CLI 修改，以及 Webhook 和 Telegram client 测试。 / Telegram schemas, client, router, capture service, app-factory and CLI updates, plus Webhook and Telegram-client tests.

**接口 / Interfaces:**

- 产出 / Produces: `TelegramUpdate`, `TelegramClient`, `create_capture_from_update`
- 产出 / Produces: 认证 Webhook 与 Webhook 注册 CLI / Authenticated Webhook and Webhook-registration CLI
- 依赖 / Consumes: 先前任务的 models、settings、单管理员与 sessionmaker / Models, settings, the single admin, and sessionmaker from earlier tasks

**执行步骤 / Execution steps:**

1. 编写 Header 密钥、路径密钥、发送者身份与重复投递的失败测试。 / Write failing tests for the header secret, path secret, sender identity, and duplicate delivery.
2. 运行聚焦测试并确认 Webhook 未注册。 / Run focused tests and confirm the Webhook is not registered.
3. 实现严格 Telegram schema 与原子 capture service；原始 JSON 和文本原样保存。 / Implement strict Telegram schemas and an atomic capture service that preserves raw JSON and text exactly.
4. 使用恒定时间比较校验两个密钥，限制已配置的私聊用户，在写入前完成全部认证。 / Validate both secrets with constant-time comparison, restrict the configured private-chat user, and finish all authentication before writes.
5. 对非文本 Update 保存原始来源但不创建标准化任务；数据库提交后才发布 Redis 或调用 Telegram API。 / Persist unsupported non-text updates as raw sources without creating normalization jobs; publish to Redis or call Telegram only after database commit.
6. 运行 Webhook、client、日志泄密与幂等测试后独立提交。 / Run Webhook, client, secret-leak, and idempotency tests, then commit independently.

**验证 / Verification:**

```powershell
uv run pytest tests/test_telegram_webhook.py tests/test_telegram_client.py -v
uv run ruff check app tests
```

**预期结果 / Expected result:** 错误密钥或用户不会产生写入；重复投递只生成一条采集和一个任务；日志不含密钥。 / Wrong secrets or users create no writes; duplicate delivery creates one capture and one job; logs contain no secrets.

**提交 / Commit:** `feat: capture Telegram text updates idempotently`

### 任务 6：派发并处理文本标准化任务 / Task 6: Dispatch and Process Text Normalization Jobs

**目标 / Goal:** 使用 Redis Stream 唤醒 Worker，同时以数据库任务状态保证恢复、重试与重复执行安全。 / Use Redis Streams to wake the worker while database job state guarantees recovery, retryability, and duplicate-execution safety.

**文件范围 / File scope:** jobs dispatcher、worker，Telegram router 修改，以及 dispatcher 与 worker 测试。 / Job dispatcher, worker, Telegram-router updates, and dispatcher and worker tests.

**接口 / Interfaces:**

- 产出 / Produces: `publish_job(redis, job_id)`
- 产出 / Produces: `recover_queued_jobs(session, redis)`
- 产出 / Produces: `process_job(session, job_id)`
- 产出 / Produces: `python -m app.jobs.worker`
- 依赖 / Consumes: `ProcessingJob`, `RawCapture`, `NormalizedContent`, Redis 与提交后的 job id / The listed models, Redis, and the post-commit job ID

**执行步骤 / Execution steps:**

1. 编写换行标准化、空格保留、任务重复处理与派发恢复的失败测试。 / Write failing tests for newline normalization, whitespace preservation, duplicate processing, and dispatch recovery.
2. 运行聚焦测试并确认 worker 模块缺失。 / Run focused tests and confirm the worker module is missing.
3. 实现 Redis Stream 发布，并在启动或恢复流程中重新发布数据库内仍为 queued 的任务。 / Implement Redis Stream publication and republish database jobs still marked queued during startup or recovery.
4. 使用事务与行锁领取任务；派生记录具有唯一约束，重复处理直接返回已完成状态。 / Claim jobs with transactions and row locks; give derived records a unique constraint and return the completed state on duplicate processing.
5. 仅规范换行，不擅自压缩用户的空格或改写内容。 / Normalize line endings only, without collapsing user spacing or rewriting content.
6. 在真实 PostgreSQL 与 Redis 上运行 worker 测试后独立提交。 / Run worker tests against real PostgreSQL and Redis, then commit independently.

**验证 / Verification:**

```powershell
uv run pytest tests/test_dispatcher.py tests/test_worker.py -v
uv run ruff check app tests
uv run ruff format --check app tests
```

**预期结果 / Expected result:** Stream 消息包含 job id；queued 任务可恢复；重复处理只产生一个派生记录；原始文本逐字节不变。 / Stream messages include the job ID; queued jobs recover; duplicate processing creates one derivation; raw text remains byte-for-byte unchanged.

**提交 / Commit:** `feat: process text captures asynchronously`

### 任务 7：加入受认证的采集 Feed Dashboard / Task 7: Add the Authenticated Capture Feed Dashboard

**目标 / Goal:** 建立第一版 Dashboard，让管理员登录后按时间查看 Telegram Spark、标准化结果与处理状态。 / Build the first Dashboard so the logged-in admin can view Telegram Sparks, normalized results, and processing states in time order.

**文件范围 / File scope:** pnpm workspace、Next.js 配置、登录页、首页、全局样式、capture feed component、typed API client、前端测试，以及 FastAPI capture router 和 API 测试。 / The pnpm workspace, Next.js configuration, login page, home page, global styles, capture-feed component, typed API client, frontend tests, FastAPI capture router, and API tests.

**接口 / Interfaces:**

- 产出 / Produces: 受认证、按 cursor 分页的 capture API / Authenticated cursor-paginated capture API
- 产出 / Produces: 登录页、受保护 Feed 与 capture cards / Login page, protected feed, and capture cards
- 依赖 / Consumes: `require_user`, `RawCapture`, `NormalizedContent` 与 auth endpoints / The listed dependency, models, and auth endpoints

**执行步骤 / Execution steps:**

1. 编写失败的 capture-feed API 测试，证明结果按当前用户隔离。 / Write a failing capture-feed API test proving results are scoped to the current user.
2. 实现最大 100 条的 cursor pagination，按 `(created_at DESC, id DESC)` 排序，并返回原文、标准化文本和处理状态。 / Implement cursor pagination capped at 100, ordered by `(created_at DESC, id DESC)`, returning original text, normalized text, and processing state.
3. 创建固定版本的 Next.js 与 pnpm workspace。 / Scaffold the pinned Next.js and pnpm workspace.
4. 编写 capture card 的失败组件测试。 / Write a failing component test for capture cards.
5. 实现类型化 API schema、登录流程、未认证重定向与受保护 Feed。 / Implement typed API schemas, login flow, unauthenticated redirect, and the protected feed.
6. 运行前后端测试、ESLint、TypeScript 和 Ruff。 / Run frontend and backend tests, ESLint, TypeScript, and Ruff.
7. 独立提交第一版 Dashboard。 / Commit the first Dashboard independently.

**验证 / Verification:**

```powershell
pnpm --dir apps/web check
Set-Location services/api
uv run pytest tests/test_capture_feed.py -v
uv run ruff check app tests
```

**预期结果 / Expected result:** 组件与 API 测试通过，ESLint、TypeScript 和 Ruff 均以状态码 0 退出。 / Component and API tests pass, while ESLint, TypeScript, and Ruff all exit with status 0.

**提交 / Commit:** `feat: show captured Sparks in Dashboard`

### 任务 8：容器化垂直切片并完成端到端证明 / Task 8: Containerize the Vertical Slice and Prove It End to End

**目标 / Goal:** 让完整垂直切片通过一条 Compose 命令运行，并由 Playwright 与 CI 证明 Telegram 到 Dashboard 的主路径。 / Make the complete vertical slice runnable with one Compose command and prove the Telegram-to-Dashboard path with Playwright and CI.

**文件范围 / File scope:** API 与 Web Dockerfile、Compose 完整服务、Playwright 配置和 E2E 场景、GitHub Actions CI，以及 README 状态与运行说明。 / API and Web Dockerfiles, full Compose services, Playwright configuration and E2E scenario, GitHub Actions CI, and README status and run instructions.

**接口 / Interfaces:**

- 产出 / Produces: `docker compose up --build` 可运行系统与 CI validation / A system runnable by `docker compose up --build` plus CI validation
- 依赖 / Consumes: 任务 1–7 的全部接口 / All interfaces from Tasks 1–7

**执行步骤 / Execution steps:**

1. 先写 Playwright 场景：投递 Telegram Update、登录、等待 Worker、在 Feed 找到消息。 / First write the Playwright scenario: deliver a Telegram update, log in, wait for the worker, and find the message in the feed.
2. 在容器连线前运行场景，确认其因应用未启动而失败。 / Run the scenario before container wiring and confirm it fails because the application is not running.
3. 加入 API、Worker 与 Web 生产容器；API 启动前执行 migration，所有依赖使用健康检查。 / Add production API, worker, and web containers; run migrations before API startup and use health checks for every dependency.
4. 加入使用 PostgreSQL 与 Redis service containers 的 CI，执行后端、前端和构建检查。 / Add CI with PostgreSQL and Redis service containers, running backend, frontend, and build checks.
5. 从干净的 Compose 状态运行完整 E2E、全部 Python 测试、静态检查和 Web production build。 / From a clean Compose state, run the complete E2E flow, all Python tests, static checks, and the Web production build.
6. 更新 README 的真实状态和精确启动命令，明确尚未进入第一阶段的功能。 / Update README with the actual status and exact startup commands, clearly naming features outside Milestone 1.
7. 独立提交可运行垂直切片。 / Commit the runnable vertical slice independently.

**验证 / Verification:**

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

**预期结果 / Expected result:** Playwright 证明 Telegram 文本可以进入 Dashboard；全部 Python、前端与构建检查通过。 / Playwright proves that Telegram text reaches the Dashboard; every Python, frontend, and build check passes.

**提交 / Commit:** `feat: deliver Telegram text capture vertical slice`

## 三、第一阶段完成定义 / Milestone 1 Definition of Done

只有同时满足以下条件，阶段 1 才算完成。 / Milestone 1 is complete only when every condition below is satisfied.

- 八个任务按顺序完成，并各自保留可审查提交。 / All eight tasks are completed in order with independently reviewable commits.
- 全新环境可通过文档命令启动，不依赖开发者机器上的隐式状态。 / A clean environment starts through documented commands without hidden developer-machine state.
- Telegram 认证、用户限制与幂等约束均由自动化测试覆盖。 / Telegram authentication, user restriction, and idempotency constraints are covered by automated tests.
- 原始采集在处理前后保持不变。 / Raw captures remain unchanged before and after processing.
- Redis 故障不会让数据库中的 queued 任务永久丢失。 / A Redis failure cannot permanently lose queued database jobs.
- 未登录用户无法读取采集 Feed。 / An unauthenticated user cannot read the capture feed.
- E2E 测试证明一次 Telegram 文本投递最终出现在 Dashboard。 / The E2E test proves that a Telegram text delivery eventually appears in the Dashboard.
- README 只声明已经实现并验证的能力。 / README claims only capabilities that have been implemented and verified.
