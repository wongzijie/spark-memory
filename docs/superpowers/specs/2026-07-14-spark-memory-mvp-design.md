# Spark Memory MVP Design

- Status: Approved in conversation; awaiting written-spec review
- Date: 2026-07-14
- Product name: Spark Memory
- Initial delivery: Single-account, self-hosted MVP

## 1. Product Summary

Spark Memory is an Agent-driven notebook for people who want to capture ideas before organizing them. The user sends unstructured, cross-domain thoughts through Telegram as text, audio, handwritten images, files, or video. The system preserves the original input, uses an LLM to decide how it should be organized, continuously maintains a compounding personal knowledge base, and proactively follows items that need future attention.

The MVP has two primary surfaces:

1. A Telegram Bot for low-friction capture, natural-language commands, reminders, and follow-up conversations.
2. A web Dashboard for viewing, searching, editing, linking, reviewing, and managing detailed memories and memory books.

The central product promise is: **capture first; organize, connect, maintain, and review automatically afterward.**

## 2. Product Principles

1. **No classification before capture.** The user never has to choose a folder, type, or workflow before recording a thought.
2. **The original is never destroyed.** Raw text and media are immutable evidence. Agent-generated content is derived and versioned.
3. **Organization is many-to-many.** A note or knowledge page may belong to multiple memory books.
4. **Knowledge compounds.** New input updates durable, interlinked knowledge pages instead of remaining a pile of isolated notes.
5. **Agent actions are explainable and reversible.** Every mutation records its reason, source, model run, and previous version.
6. **Uncertainty controls interruption.** High-confidence, low-risk work happens silently; consequential ambiguity is surfaced.
7. **Follow-up is stateful.** Running-up notes have explicit goals, conditions, status, evidence, and next-check times.
8. **External facts require provenance.** Tavily results are stored with URLs, retrieval times, and the claims they support.
9. **Human and Agent content remain distinguishable.** The system never presents an Agent synthesis as the user's original words.
10. **The MVP stays operable.** It favors a small set of durable services and avoids premature infrastructure such as a dedicated graph database.

## 3. MVP Scope

### 3.1 Included

- One pre-provisioned Dashboard account.
- Telegram Bot capture and interaction.
- Text, audio/voice, handwritten image, general image, document, and video input.
- Automatic classification into simple, real-time, and running-up note behavior.
- One-time and recurring scheduled tasks created in natural language.
- Tavily-backed internet follow-up for notes that depend on changing external facts.
- Agent-maintained living knowledge pages and typed relationships.
- Memory-book creation and management with many-to-many membership.
- Full-text, semantic, temporal, status, and graph-assisted retrieval.
- Source provenance, version history, undo, archive, recycle bin, and reprocessing.
- Dashboard Settings for the Telegram Bot Token, cloud-model API Key, and Tavily API Key.
- Docker Compose deployment on one cloud server.
- Daily backups and a tested restore path.

### 3.2 Excluded from the MVP

- Public registration and production multi-tenant operation.
- Native iOS or Android applications.
- Google Calendar or other external calendar integrations.
- A global interactive graph visualization.
- Local model inference.
- Fine-tuning a personal model.
- Autonomous external actions such as sending emails, purchasing, or publishing.
- User-selectable support for multiple model vendors in the UI.

The schema includes `user_id` from the first migration, and the provider layer remains replaceable, so these exclusions do not block later expansion.

## 4. Terminology

| Term | Definition |
| --- | --- |
| Spark | One raw capture event received from Telegram. |
| Raw capture | Immutable text, metadata, and attachment references as received. |
| Canonical note | The current readable interpretation of one or more Sparks. |
| Memory page | A durable Agent-maintained page about a person, topic, project, goal, event, question, decision, or source. |
| Claim | A specific statement with provenance, confidence, and validity time. |
| Memory edge | A typed relationship between notes, pages, claims, or other entities. |
| Memory book | A user-facing collection or view; it is not an exclusive folder. |
| Real-time note | A bounded session made from multiple semantically continuous captures. |
| Running-up note | A stateful item whose objective needs intelligent future checking or user follow-up. |
| Scheduled task | A deterministic one-time or recurring reminder without an expanding research objective. |
| Agent Schema | Versioned rules for page types, naming, classification, merging, provenance, and maintenance. |
| Lint | A periodic health check for contradictions, staleness, duplicates, orphans, and missing connections. |

## 5. Reference Pattern: Karpathy LLM Wiki

The memory architecture adapts Andrej Karpathy's April 2026 [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):

- immutable raw sources;
- an LLM-owned, persistent, interlinked wiki;
- a co-evolving schema that disciplines the Agent;
- ingest, query, and lint operations that make knowledge compound;
- a content index and chronological change log;
- filing valuable query outputs back into the knowledge base.

Spark Memory extends this pattern for a continuously arriving, multimodal personal stream. It adds claim-level provenance, temporal validity, typed edges, reversible mutations, memory books, running-up state machines, scheduled follow-up, and hybrid retrieval at larger scale.

## 6. System Architecture

### 6.1 Services

| Service | Responsibility |
| --- | --- |
| `web` | Next.js Dashboard, authenticated user interface, and server-rendered views. |
| `api` | FastAPI business API, Telegram Webhook, account/session endpoints, and Settings endpoints. |
| `worker` | Multimodal normalization, LLM calls, Knowledge Compiler, embeddings, lint, and retryable jobs. |
| `scheduler` | Due scheduled tasks, running-up checks, recurring lint, and maintenance triggers. |
| `postgres` | PostgreSQL plus pgvector for product data, full-text search, vectors, graph edges, versions, and audit records. |
| `redis` | Durable job coordination, locks, rate limiting, idempotency assistance, and short-lived state. |
| `minio` | Private S3-compatible object storage for original audio, images, videos, documents, and generated derivatives. |
| reverse proxy | HTTPS termination and routing to `web` and `api`. |

The initial deployment uses Docker Compose on one cloud server. Services communicate over a private Docker network. PostgreSQL, Redis, and object storage are not publicly exposed.

### 6.2 External Services

- Telegram Bot API for capture and notifications.
- One OpenAI-compatible cloud model provider in the MVP, with an OpenAI preset and configurable API key, base URL, and model identifiers on the server side.
- Tavily for internet search used by running-up and freshness checks.

### 6.3 Reliability Boundary

The synchronous Telegram Webhook performs only authentication, idempotency checks, raw persistence, job creation, and a short acknowledgement. It does not wait for transcription or an LLM. Expensive work is asynchronous.

A raw capture and its processing job are committed atomically. If a downstream dependency fails, the original input remains available and the job can be replayed.

## 7. Core Memory Model

### 7.1 Four Layers

1. **Raw layer:** immutable Telegram messages, media metadata, downloaded original objects, and source hashes.
2. **Interpreted layer:** normalized text, transcription, OCR, visual descriptions, canonical notes, and detected language/time references.
3. **Living knowledge layer:** durable memory pages, claims, summaries, and typed relationships maintained by the Knowledge Compiler.
4. **User organization layer:** memory books, saved filters, pins, archives, and Dashboard presentation.

The Agent Schema governs transformations between layers. It is stored as versioned data and exported as readable Markdown for inspection. The Agent authors the initial organizational rules. A direct user correction creates an immediate scoped override; changes that would alter global classification, page types, edge vocabulary, or safety rules are proposed in Review and become a new schema version only after approval.

### 7.2 Core Entities

Every entity includes `user_id`, creation/update timestamps, and soft-deletion metadata where applicable.

| Entity | Purpose |
| --- | --- |
| `User` | Account identity and tenant boundary, even though the MVP has one account. |
| `ProviderCredential` | Encrypted Telegram, model, and Tavily secrets plus validation state. |
| `RawCapture` | Immutable Telegram update, sender/chat metadata, original text, and idempotency key. |
| `Attachment` | Object key, media type, size, hash, Telegram metadata, and derivative links. |
| `ProcessingJob` | Durable processing state, attempts, error category, and retry schedule. |
| `CanonicalNote` | Current organized note produced from one or more raw captures. |
| `NoteVersion` | Append-only history of canonical-note content and metadata. |
| `MemoryPage` | Current living page for a typed durable concept or entity. |
| `PageVersion` | Append-only history of a memory page. |
| `Claim` | Atomic statement, confidence, valid-from/valid-to time, and lifecycle status. |
| `SourceReference` | Link from a note, page, or claim to a raw capture or external Tavily result. |
| `MemoryEdge` | Typed directed relation with confidence, validity time, and source references. |
| `MemoryBook` | Named user-facing collection with description and optional Agent guidance. |
| `BookMembership` | Many-to-many link from a note or page to a memory book. |
| `RealtimeSession` | Active/closed capture session and rolling summary. |
| `FollowUp` | Running-up objective, completion condition, policy, status, and next-check time. |
| `ScheduledTask` | Deterministic time expression, recurrence rule, timezone, and next occurrence. |
| `AgentRun` | Model/provider, prompt/schema versions, inputs, structured decision, cost, and outcome. |
| `ChangeSet` | A validated transactional group of Agent mutations and its undo information. |
| `ExternalSearch` | Tavily query, results, retrieval time, deduplication key, and linked claims. |
| `AgentSchemaVersion` | Versioned classification and maintenance rules. |

### 7.3 Memory Page Types

The MVP supports these page types: `person`, `organization`, `topic`, `project`, `goal`, `event`, `decision`, `question`, and `source`. The Agent may propose an alias or a new page, but it may not invent a new page type without changing the Agent Schema.

Create a new page when an item is a distinct reusable entity or concept that other pages can link to. Update an existing page when the input adds an attribute, observation, development, or correction to that page.

### 7.4 Edge Types

The initial controlled vocabulary is:

- `related_to`
- `member_of`
- `mentions`
- `supports`
- `contradicts`
- `updates`
- `depends_on`
- `caused_by`
- `part_of`
- `derived_from`
- `same_as`
- `about`

Every nontrivial edge records evidence and confidence. The Agent may propose a new edge type through an Agent Schema change, but it may not silently create arbitrary predicates.

### 7.5 Knowledge Integrity Rules

- Raw captures and original attachments are immutable.
- Current notes/pages are editable, but every edit creates a version.
- A derived claim must have at least one `SourceReference` or be explicitly marked `agent_inference`.
- An Agent inference may not be silently promoted to a sourced fact.
- Contradictory claims coexist until evidence or the user resolves them.
- A newer claim can mark an older claim `superseded`; it does not delete it.
- Deleting a memory book does not delete its notes or pages.
- Hard deletion removes originals, derivatives, embeddings, memberships, and source-linked generated content after the recycle-bin retention period.

## 8. Knowledge Compiler and Retrieval

### 8.1 Knowledge Compiler

For each processed Spark or closed real-time session, the compiler:

1. reads normalized content and media-derived text;
2. retrieves likely existing pages and notes;
3. detects entities, claims, time references, intent, and note behavior;
4. decides whether to create, update, link, or leave content uncompiled;
5. generates a structured `ChangeSet` rather than writing directly;
6. validates provenance, permissions, controlled types, and invariants;
7. commits the complete change set transactionally;
8. updates search indexes and embeddings;
9. records an `AgentRun` and sends only necessary notifications.

The Agent can automatically assign content to existing memory books. When it believes a new memory book is needed, it creates a proposal in Review rather than creating the book silently.

### 8.2 Confidence Policy

Confidence is a rubric-driven enum, not an uncalibrated model percentage:

- **High:** one clear target, no conflicting critical fields, all required provenance present. Execute and log.
- **Medium:** a best target exists, but a noncritical alternative or weak relation remains. Execute, label for passive Review, and allow undo.
- **Low:** merge target is ambiguous, provenance is missing, or a critical time/goal field is uncertain. Preserve independently and request review.

The Bot interrupts immediately only when ambiguity affects a commitment, deadline, destructive merge, or running-up completion condition.

### 8.3 Retrieval Pipeline

The system never sends the full knowledge base to the model as it grows. Retrieval proceeds in stages:

1. route by user, memory book, entity/page type, status, time, and lightweight index summaries;
2. retrieve candidates using PostgreSQL full-text search and pgvector similarity;
3. expand one or two graph hops around high-quality candidates;
4. add recency, source quality, and running-up relevance signals;
5. rerank and deduplicate candidates;
6. pack only the most relevant full pages, claims, and sources into the model context.

Query answers cite the underlying memory sources. A query answer is automatically filed back only when it is source-backed, introduces a reusable synthesis that is not already represented, and passes the high-confidence ChangeSet rubric. All other potentially durable answers become Review proposals. Transient conversation is not stored as knowledge.

### 8.4 Lint

Lightweight lint runs daily and checks recent changes plus active running-up items. Full-graph lint runs weekly. Both schedules are server-configurable. Lint checks for:

- duplicate or near-duplicate pages;
- contradictory claims;
- stale externally changing claims;
- orphan pages and missing inbound links;
- important repeated concepts without a page;
- broken source references;
- under-updated cross-references;
- dormant running-up items;
- memory-book drift and noisy classifications.

Lint creates suggestions or safe change sets. It does not hard-delete data. External freshness checks use Tavily only when the claim is time-sensitive and the configured budget permits it.

## 9. Multimodal Processing

| Input | MVP processing |
| --- | --- |
| Text | Preserve original formatting, detect language, normalize metadata, and compile. |
| Voice/audio | Store original, transcribe, preserve timestamps when available, and compile transcript plus audio reference. |
| Handwritten/general image | Store original, run OCR and vision understanding, retain extracted text and image reference. |
| Document | Store original, extract supported text and metadata, and retain page/source locations. |
| Video | Store original, extract audio for transcription, sample scene-change and interval keyframes, analyze selected frames, and create a combined transcript/visual summary. |

Long media is processed asynchronously. Configured size and duration limits are shown before upload or in the Bot's response. Unsupported or oversized inputs remain saved with a clear processing status rather than being discarded.

## 10. Note Behaviors

### 10.1 Simple Notes

Simple notes are captured, normalized, linked, and compiled without future autonomous checking. They can still update living pages and belong to multiple memory books.

### 10.2 Real-Time Notes

The Agent groups captures using reply relationships, semantic continuity, and time proximity. The default active-session idle window is 30 minutes and is configurable through server configuration.

- A related capture inside the window joins the active session.
- An unrelated capture remains independent even if it arrives inside the window.
- `/close` closes the active session immediately.
- Idle expiry closes the session and schedules final compilation.
- A rolling summary supports long sessions without repeatedly loading every full message.
- The user can split an incorrect session or merge independent notes from the Dashboard.

### 10.3 Running-Up Notes

A running-up item contains:

- objective;
- completion condition;
- current status;
- next check time;
- whether checking requires the user, the web, or both;
- search scope and trusted-source hints;
- evidence gathered so far;
- maximum per-check search budget;
- retry/backoff state;
- link to originating notes and affected memory pages.

States are `active`, `checking`, `awaiting_user`, `updated`, `scheduled`, `completed`, and `cancelled`.

At the next check, the Follow-up Agent may query Tavily, compare evidence with existing claims, update the living page, ask the user a targeted question, mark the item complete, or schedule a new check. It may not perform an external side effect beyond search and Telegram messaging.

### 10.4 Scheduled Tasks

The user can create one-time or recurring reminders in natural language. The parser produces an explicit local time, IANA timezone, recurrence rule, and next occurrence for confirmation when the expression is ambiguous.

Scheduled tasks send deterministic Telegram reminders. They do not perform Tavily research or evolve into broader objectives unless the user or Agent explicitly converts them to running-up items.

## 11. Tavily Search Policy

- Tavily is the only internet-search provider in the MVP.
- Every search is attached to a running-up, lint, or explicit user-query purpose.
- Queries, result URLs, titles, snippets, retrieval times, and result hashes are recorded.
- Results are deduplicated across repeated checks.
- Search-derived claims link to the supporting result and retrieval time.
- The Agent distinguishes a search result snippet from verified page content.
- No-change checks use the follow-up policy to select the next time rather than looping continuously.
- Model and Tavily budgets are enforced per day and per follow-up.
- Three consecutive dependency failures move a job to `needs_attention` after exponential retry and notify the user once.

## 12. Telegram Experience

### 12.1 Default Interaction

- Any supported input is a capture; no pre-classification is requested.
- The Bot responds quickly with a capture acknowledgement.
- Long media receives a second message on completion or failure.
- Routine high-confidence organization is silent.
- Critical ambiguity produces one targeted question.
- Running-up findings include the change, evidence link, current conclusion, and next action.

### 12.2 Commands

The MVP includes:

- `/today` — today's captures, reminders, and follow-ups;
- `/followups` — active running-up items;
- `/tasks` — upcoming deterministic tasks;
- `/close` — close the active real-time session;
- `/undo` — undo the latest reversible Agent change;
- `/search` — search memories;
- `/settings` — link to Dashboard Settings.

Every command also has a natural-language equivalent. The user can correct behavior conversationally, for example: “undo that merge” or “do not put this kind of note in the startup memory book.” Corrections create explicit overrides or versioned Agent Schema changes.

## 13. Dashboard Experience

The selected layout is the **Memory Workspace**:

### 13.1 Left Navigation

- Today
- All memories
- Running-up
- Scheduled tasks
- Review
- Memory books
- Archive
- Recycle bin
- Settings

### 13.2 Center Workspace

The center shows a time-ordered stream of Sparks, canonical notes, real-time sessions, and memory-page updates. It supports full-text search, semantic search, filters, saved views, processing status, and bulk selection where safe.

A compact Agent Briefing at the top surfaces recent updates, notable follow-ups, failures, and high-value Review items without turning the product into an inbox that must be cleared.

### 13.3 Detail Panel

The right panel shows:

- current readable content;
- note/page type and status;
- memory-book memberships;
- local related-memory graph;
- original captures and attachments;
- claims and Tavily sources;
- Agent explanation and confidence;
- version/change timeline;
- processing and follow-up state.

### 13.4 Management Actions

The user can edit, rename, pin, archive, delete, restore, merge, split, change type, change memory-book membership, correct relationships, inspect sources, restore versions, undo Agent changes, and re-run failed processing.

Memory books can be created, renamed, described, merged, archived, and deleted. A book description may include natural-language Agent guidance. Book deletion removes memberships but not memories.

The MVP shows local relationships in the detail panel. A global interactive graph view is deferred.

## 14. Settings and Credential Management

The Settings entry is present in the MVP even though public registration is deferred. General Settings also include the account timezone, defaulting to `Asia/Shanghai`; every parsed task stores its own IANA timezone.

### 14.1 First-Run Account

The deployment runs a one-time CLI bootstrap command that creates the single admin account and prompts for its initial password. The command refuses to create a second account. There is no public registration endpoint. Login uses a server-side session in an HTTP-only, secure, same-site cookie.

### 14.2 Telegram Bot Connection

1. The user enters a Bot Token.
2. The backend validates it with Telegram and displays the bot identity.
3. The backend registers a unique secret Webhook.
4. The Dashboard produces a one-time `/start` link/code.
5. The user sends it to the bot, binding the Telegram user ID to the Dashboard account.
6. The Bot rejects updates from any unbound Telegram user.

### 14.3 Key Handling

- The MVP stores the Telegram Bot Token, cloud-model API Key, and Tavily API Key.
- Secrets are encrypted with AES-256-GCM using a server master key that is never stored in the database.
- The browser receives only masked values and validation metadata after save.
- Decrypted secrets exist only in server/worker memory for the duration required to call a provider.
- Logs, traces, exceptions, and Agent inputs redact secret-looking values.
- The user can test, replace, disable, or delete a credential.
- Deleting a credential stops dependent jobs and explains which features are unavailable.

The data model supports per-user credentials. A later release can add registration and isolated user onboarding without redesigning provider ownership.

## 15. Error Handling and Idempotency

### 15.1 Telegram Delivery

Telegram's update ID plus bot/account identity forms the capture idempotency key. Replayed Webhook updates return success without creating duplicate captures.

### 15.2 Agent Mutations

The Agent never writes arbitrary partial updates. It produces a structured `ChangeSet`, validation runs before mutation, and all database mutations commit in one transaction. Indexing and embedding updates are replayable follow-on jobs.

### 15.3 Retries

Errors are classified as transient, credential, policy/budget, invalid input, or permanent. Transient failures retry with bounded exponential backoff. Credential failures pause dependent jobs until the key is fixed. Permanent failures preserve the raw capture and expose a reprocess action.

### 15.4 User Visibility

The Dashboard displays `queued`, `processing`, `processed`, `needs_attention`, and `failed` states. It shows a user-readable failure reason without exposing secrets or raw provider traces.

### 15.5 Undo

Every reversible Agent change records inverse operations or the prior version. Undo creates a new version; it does not erase audit history. Hard deletion is not an Agent action and requires explicit user confirmation.

## 16. Security, Privacy, and Operations

- HTTPS is mandatory outside local development.
- PostgreSQL, Redis, and object storage are private-network only.
- Telegram Webhooks use a unique secret and validate the expected bot binding.
- All database queries and jobs are scoped by `user_id`.
- Provider calls receive only task-relevant content.
- Provider, purpose, time, related memory, token/cost metadata, and outcome are logged without secrets.
- Object-store buckets are private; access uses short-lived server-generated URLs.
- The system applies upload size, media duration, request-rate, model-cost, and Tavily-search limits.
- Daily encrypted backups include PostgreSQL and MinIO objects. The MVP retains seven daily backups and four weekly backups. Redis is not the source of truth.
- A restore drill must succeed before the MVP is declared ready.
- Recycle-bin retention defaults to 30 days. After that period, deletion propagates to originals, derivatives, embeddings, memberships, and exclusively source-linked generated content.

## 17. Testing Strategy

### 17.1 Unit Tests

- note-behavior rubric;
- recurrence and timezone parsing;
- real-time session boundaries;
- running-up state transitions;
- confidence/risk routing;
- ChangeSet validation;
- graph and provenance invariants;
- credential encryption and redaction;
- access scoping and idempotency.

### 17.2 Integration Tests

- PostgreSQL and pgvector retrieval;
- Redis-backed worker/scheduler behavior;
- object-storage upload and deletion;
- Telegram Webhook and Bot responses;
- cloud-model adapter with recorded fixtures or mocks;
- Tavily adapter with recorded fixtures or mocks;
- Webhook registration and Telegram account binding.

### 17.3 End-to-End Tests

- Telegram capture appears in the Dashboard with its original source.
- Voice, handwriting, and video produce derived content while preserving originals.
- A related message joins a real-time session and `/close` compiles it.
- A running-up item performs a Tavily check, stores evidence, updates status, and schedules the next check.
- A natural-language recurring reminder fires through Telegram.
- A Dashboard correction changes the current note and creates an audit version.
- An invalid provider key is visible, recoverable, and does not lose queued captures.

### 17.4 Fault Tests

- duplicate Telegram updates;
- API timeout and rate limiting;
- worker restart mid-job;
- scheduler restart with overdue jobs;
- database transaction rollback;
- missing attachment or object-store interruption;
- exhausted model or Tavily budget;
- restore from backup.

## 18. MVP Acceptance Criteria

The MVP is complete only when all of these are demonstrated in a deployed environment:

1. Text, voice, handwritten image, document, and video captures are durably saved.
2. The Agent automatically distinguishes simple, real-time, and running-up behavior.
3. Real-time sessions group related captures and can be closed, split, or merged.
4. Running-up uses Tavily with stored provenance and a durable next-check state.
5. One-time and recurring scheduled tasks notify through Telegram.
6. The Dashboard can search, view, edit, merge, split, archive, delete, restore, and reclassify memories.
7. Every Agent mutation is sourced, versioned, explainable, and reversible.
8. Temporary provider or worker failure never loses a raw capture.
9. Settings can securely add, validate, replace, disable, and delete the three MVP credentials.
10. Backup restoration reproduces the database records and original attachments.
11. Automated unit, integration, end-to-end, and fault tests for the critical flows pass.

## 19. Post-MVP Evolution

The next phase can introduce public registration, account verification and recovery, tenant quotas, per-user Bot onboarding, subscription/billing controls, and operational abuse protection. Later phases can add native mobile capture, additional model/search providers, external calendar integrations, a global graph explorer, and optional local models.

These changes build on the existing `user_id` boundary, encrypted per-user credentials, provider adapters, and graph-aware memory model; they do not require replacing the core architecture.
