# Spark Memory

> 先捕捉，再整理。让 Agent 帮你连接、维护和跟进记忆。

Spark Memory 是一个正在设计和开发中的 **Agent 驱动多模态笔记本**。它面向不愿在记录灵感前先分类的人：用户只管把转瞬即逝的想法发进来，系统负责在之后理解内容、建立关联、更新长期知识，并主动跟进需要持续关注的事项。

**English summary:** Spark Memory is an Agent-driven, multimodal notebook that captures unstructured thoughts first and organizes them afterward. It turns an ongoing stream of text, voice, handwriting, images, and video into a source-backed, evolving personal knowledge system with intelligent follow-up.

## 项目状态

> [!IMPORTANT]
> 当前仓库已经交付 **Milestone 1：Telegram 文字捕捉垂直切片**。它可以通过 Docker Compose 运行：安全接收 Telegram 文字、不可变保存原始 Update、经 Redis Worker 异步标准化，并在受登录保护的中英双语 Dashboard 中显示。

- **Current status:** Milestone 1 is runnable end to end. Telegram text is stored idempotently, normalized by a Redis Stream worker, and shown in an authenticated bilingual Dashboard.
- 已完成：单管理员认证、Telegram 双 Secret 校验、发送者白名单、PostgreSQL/Redis 持久化、异步 Worker、Dashboard、Docker Compose、CI 与 Playwright 主路径测试
- 下一步：Agent 分类与长期记忆编译，然后是多模态、Running-up 和 Tavily 联网跟进
- 完整规格：[Spark Memory MVP Design](docs/superpowers/specs/2026-07-14-spark-memory-mvp-design.md)

## 本地运行 / Run locally

需要 Docker Desktop。把 `.env.example` 复制为 `.env`，并替换云端模型、Tavily、Telegram Bot Token、Telegram 用户 ID、Webhook 双 Secret 和公网 HTTPS 地址；不要提交 `.env`。

Docker Desktop is required. Copy `.env.example` to `.env` and replace the cloud-model, Tavily, Telegram bot token, allowed Telegram user ID, both webhook secrets, and public HTTPS URL values. Never commit `.env`.

当前云端模型配置采用 OpenAI-compatible 接口，通过 `SPARK_LLM_BASE_URL`、`SPARK_LLM_MODEL` 和 `SPARK_LLM_API_KEY` 注入；Tavily 使用 `SPARK_TAVILY_BASE_URL` 与 `SPARK_TAVILY_API_KEY`。这些配置会同时传入 API 和 Worker，但完整的 Agent 分类与联网跟进工作流仍属于后续里程碑。

The cloud model uses an OpenAI-compatible endpoint configured through `SPARK_LLM_BASE_URL`, `SPARK_LLM_MODEL`, and `SPARK_LLM_API_KEY`. Tavily uses `SPARK_TAVILY_BASE_URL` and `SPARK_TAVILY_API_KEY`. Both API and Worker receive these values; the complete Agent organization and web-follow-up workflows remain later milestones.

```powershell
docker compose up -d --build

$env:SPARK_ADMIN_PASSWORD = "choose-a-long-local-password"
$env:SPARK_ADMIN_PASSWORD | docker compose exec -T api python -m app.cli create-admin --email owner@example.com --password-stdin
```

打开 [http://localhost:3000](http://localhost:3000)，使用刚创建的邮箱和密码登录。API readiness 位于 [http://localhost:8000/health/ready](http://localhost:8000/health/ready)。

Open [http://localhost:3000](http://localhost:3000) and sign in with the account you just created. API readiness is available at [http://localhost:8000/health/ready](http://localhost:8000/health/ready).

### 一键本地命令 / One-command local lifecycle

将仓库的 `scripts` 目录加入 Windows 用户 PATH 后，可以在任意新终端运行：

After adding the repository `scripts` directory to the Windows user PATH, run these commands from any new terminal:

```powershell
spark go      # 启动、构建并配置本地管理员 / start, build, and configure the admin
spark reboot  # 强制重建并重启 / recreate and restart
spark stop    # 停止服务但保留数据库卷 / stop while preserving database volumes
```

管理员邮箱和密码来自 Git 忽略的本机 `.env` 中的 `SPARK_ADMIN_EMAIL` 与 `SPARK_ADMIN_PASSWORD`。

The administrator email and password come from `SPARK_ADMIN_EMAIL` and `SPARK_ADMIN_PASSWORD` in the Git-ignored local `.env`.

### 注册 Telegram Webhook / Register the Telegram webhook

确保 `.env` 中的 `SPARK_PUBLIC_BASE_URL` 是能转发到 API 8000 端口的 HTTPS 地址，然后执行：

Make sure `SPARK_PUBLIC_BASE_URL` is an HTTPS origin that routes to API port 8000, then run:

```powershell
docker compose up -d
docker compose exec api python -m app.cli register-webhook
```

### 验证与测试 / Verification and tests

```powershell
# Python API and worker
Set-Location services/api
uv sync --locked --all-groups
uv run alembic upgrade head
uv run ruff check app tests alembic
uv run ruff format --check app tests alembic
uv run pytest -v
Set-Location ../..

# Dashboard
corepack pnpm install --frozen-lockfile
corepack pnpm --dir apps/web check
corepack pnpm --dir apps/web build

# Real Telegram → Worker → Dashboard path against Compose defaults
$env:E2E_API_URL = "http://127.0.0.1:8000"
$env:E2E_WEB_URL = "http://127.0.0.1:3000"
$env:E2E_WEBHOOK_PATH = "e2e-path-secret-0000000000000001"
$env:E2E_WEBHOOK_HEADER = "e2e-header-secret-00000000000001"
$env:E2E_ADMIN_EMAIL = "owner@example.com"
$env:E2E_ADMIN_PASSWORD = "choose-a-long-local-password"
corepack pnpm --dir apps/web exec playwright install chromium
corepack pnpm --dir apps/web e2e
```

停止服务使用 `docker compose down`。`docker compose down -v` 会连同本地 PostgreSQL 与 Redis 数据一起删除。

Use `docker compose down` to stop the stack. `docker compose down -v` also deletes local PostgreSQL and Redis data.

### Milestone 1 尚未包含 / Not included yet

- Settings 与用户自助 BYOK / user-managed Settings and BYOK
- LLM 自动分类、知识图谱与 Living Wiki 编译 / LLM organization, knowledge graph, and Living Wiki compilation
- 语音、手写、图片、文档与视频处理 / voice, handwriting, image, document, and video processing
- Running-up、智能定时任务与 Tavily 联网更新 / Running-up, intelligent scheduling, and Tavily web follow-up

## 为什么做 Spark Memory

大多数笔记工具要求用户在记录前决定文件夹、标签或任务类型。但真正的灵感往往是发散的、跨领域的，而且稍纵即逝。分类本身可能打断思考；记录完成后，笔记又经常停留在原处，不会主动更新、互相勾稽或提醒用户继续推进。

Spark Memory 希望解决四个问题：

1. **记录前不分类**：Agent 在捕捉后判断内容类型和归属规则。
2. **笔记会持续生长**：新输入可以更新既有知识页面、关系和结论。
3. **跟进不只是提醒**：Running-up Agent 能根据目标、证据和状态决定下一步。
4. **输入不限于键盘**：支持文字、语音、手写图片、文档和视频。

## MVP 体验

### Telegram：低摩擦捕捉入口

用户可以直接向 Bot 发送：

- 普通文字和自然语言命令
- 语音或音频
- 手写笔记照片和一般图片
- 文档
- 视频

Bot 会先可靠保存原始内容，再在后台转写、识别、理解和整理。用户不需要预先选择笔记类型或记忆本。

### Dashboard：记忆工作台

Dashboard 采用三栏式记忆工作台：

- 左侧：今天、所有记忆、Running-up、定时任务、Review 和记忆本
- 中间：按时间展示 Spark、实时笔记和知识页面更新
- 右侧：详细内容、原始来源、关联记忆、Agent 解释和版本历史

用户可以搜索、编辑、合并、拆分、归档、恢复、重新分类，以及撤销 Agent 的修改。

## 三种笔记行为

| 类型 | 系统行为 |
| --- | --- |
| 简单笔记 | 保存、理解、关联并编译进长期知识，不主动安排未来检查。 |
| 实时笔记 | 根据时间、语义和回复关系自动聚合连续输入，结束后统一整理。 |
| Running-up | 建立目标、完成条件和下一次检查时间，通过用户追问或联网搜索持续推进。 |

普通定时任务与 Running-up 分开：前者按确定时间提醒，后者根据变化和证据动态决定下一步。

## 长期记忆：从 RAG 到持续编译的 Wiki

Spark Memory 参考了 Andrej Karpathy 的 [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思路：不让模型在每次提问时从零检索和拼接全部原始材料，而是让 Agent 持续维护一个可阅读、可追溯、会累积的知识库。

```mermaid
flowchart TD
    A["Raw Spark<br/>原始文字、语音、图片、视频"] --> B["Knowledge Compiler<br/>理解、拆解、消歧、提取主张"]
    B --> C["Living Memory Pages<br/>人物、主题、项目、目标、事件、决策"]
    C --> D["Typed Memory Graph<br/>支持、反驳、更新、依赖、相关、属于"]
    D --> E["Memory Books<br/>用户看到的多重视图"]
    F["Agent Schema<br/>分类、命名、合并和维护规则"] --> B
    G["Lint Agent<br/>重复、矛盾、过期、孤立、缺口"] --> C
    H["Running-up + Tavily"] --> C
```

核心原则：

- 原始输入不可变，Agent 生成的内容可以演化但必须保留版本
- 一条笔记可以同时属于多个记忆本
- 结论、关系和联网更新都要记录来源、时间和置信度
- 新信息与旧信息冲突时保留两种主张，而不是静默覆盖
- 有价值的查询结果可以反写为长期知识，普通闲聊不会污染知识库
- 定期 Lint 会发现重复、矛盾、过期事实、孤立页面和缺失关联

## Running-up 与 Tavily

Running-up 是持久状态机，而不是一条固定提醒。每个项目都保存目标、完成条件、当前状态、证据、下次检查时间和搜索预算。

```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> Checking: 到达检查时间
    Checking --> Updated: Tavily 发现有效变化
    Checking --> AwaitingUser: 需要用户补充
    Checking --> Scheduled: 暂无变化
    AwaitingUser --> Updated: 用户回复
    Updated --> Scheduled: 安排下次检查
    Scheduled --> Checking
    Updated --> Completed: 满足完成条件
    Active --> Cancelled: 用户取消
```

Tavily 搜索结果会保存 URL、检索时间和所支持的具体主张。系统会进行结果去重、预算控制和失败退避，不会无限搜索。

## MVP 技术架构

```mermaid
flowchart LR
    TG[Telegram Bot] --> API[FastAPI Core]
    UI[Next.js Dashboard] --> API
    API --> PG[(PostgreSQL + pgvector)]
    API --> R[(Redis)]
    API --> O[(MinIO)]
    R --> W[Agent Workers]
    S[Scheduler] --> W
    W --> AI[Cloud AI]
    W --> T[Tavily]
    W --> PG
    W --> O
```

- Next.js：Dashboard
- FastAPI/Python：业务 API、Telegram Webhook 和 Agent 服务
- PostgreSQL + pgvector：结构化数据、全文与语义检索、版本和图关系
- Redis + Worker：后台任务、锁、重试和调度协调
- MinIO：原始语音、图片、视频和文档
- Tavily：需要外部新信息的跟进和事实更新
- Docker Compose：单台云服务器上的 MVP 部署

MVP 先使用 PostgreSQL 的边表和递归查询处理图关系，不提前引入 Neo4j。达到更大规模并出现明确瓶颈后再评估专用图数据库。

## Settings 与 BYOK

第一阶段只有一个预置账户，但 Dashboard 会保留 Settings 入口。用户可以管理：

- Telegram Bot Token
- 云端模型 API Key
- Tavily API Key
- 账户时区

Key 会在服务端加密保存，浏览器只能看到掩码。后续版本将开放注册，让每个用户绑定自己的 Bot 和 API Key，形成多租户 BYOK 模式。

> [!WARNING]
> 不要把 `.env`、Bot Token、模型 Key、Tavily Key、数据库备份或个人记忆内容提交到 Git。仓库已通过 `.gitignore` 排除常见本地密钥和数据目录。

## 计划路线

- [x] 产品需求与 MVP 范围
- [x] 系统与数据架构
- [x] Karpathy LLM Wiki + 时态知识图谱设计
- [x] Telegram、Dashboard 和 Running-up 工作流
- [x] 安全、备份和验收标准
- [x] 实施计划与任务拆分
- [x] 基础设施和数据模型
- [x] Telegram 文字捕捉垂直切片
- [ ] 多模态处理
- [x] Dashboard 文字捕捉 Feed
- [ ] Running-up + Tavily
- [ ] 部署、备份和故障验证

## 参与讨论

如果你也在探索 Agent 笔记、个人知识库、LLM Wiki、GraphRAG 或长期记忆系统，欢迎通过 GitHub Issues 分享使用场景、设计反馈或实现建议。

## License

本仓库目前尚未添加开源许可证。在 `LICENSE` 文件加入之前，仓库内容仅供查看与讨论，保留所有权利。
