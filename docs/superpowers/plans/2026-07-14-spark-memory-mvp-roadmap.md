# Spark Memory MVP Delivery Roadmap

The approved MVP specification contains several independently testable subsystems. Delivery is split into seven milestones so each stage produces working software, evidence, and a stable base for the next stage.

## Milestone 1: Foundation and Telegram Text Capture

Deliver a runnable single-account system that accepts a Telegram text message, persists the immutable update, processes it asynchronously, and displays it in an authenticated Dashboard feed.

Detailed plan: [2026-07-14-spark-memory-foundation-text-capture.md](2026-07-14-spark-memory-foundation-text-capture.md)

Exit evidence:

- PostgreSQL and Redis-backed services start through Docker Compose.
- A bootstrapped admin can log in.
- An authenticated Telegram Webhook stores the update idempotently.
- A worker creates normalized derived content without modifying the raw update.
- The Dashboard displays the captured message and processing state.

## Milestone 2: Settings, Credential Vault, and Bot Onboarding

Add AES-256-GCM credential storage, masked Settings fields, provider validation, Telegram `getMe`, automatic Webhook registration, one-time account/bot binding, credential rotation, and dependency pausing after credential deletion.

Exit evidence: the admin can connect a Bot, cloud-model key, and Tavily key without editing `.env`; no saved secret is returned to the browser or logs.

## Milestone 3: Memory Workspace and Memory Books

Add canonical notes, note/page versions, memory-book CRUD, many-to-many membership, search/filter APIs, the three-column Memory Workspace, detail/source/timeline panels, archive, recycle bin, restore, merge, split, and undoable user edits.

Exit evidence: raw captures can be managed as versioned notes in multiple memory books from the Dashboard.

## Milestone 4: Knowledge Compiler and Living Memory Graph

Add the model adapter, Agent Schema versions, retrieval/reranking, structured ChangeSets, page/claim/edge/source models, provenance validation, transactionally applied mutations, query-to-wiki filing rules, and daily/weekly lint.

Exit evidence: a text note updates source-backed living pages and typed relationships; contradictions and versions remain inspectable and reversible.

## Milestone 5: Real-Time and Multimodal Capture

Add voice transcription, handwriting/image OCR and vision, document extraction, video audio/keyframe processing, object storage, media limits, real-time session grouping, rolling summaries, idle closure, `/close`, merge, and split.

Exit evidence: each supported modality reaches the same immutable-source and Knowledge Compiler pipeline, and a multi-message real-time session compiles once when closed.

## Milestone 6: Scheduled Tasks and Running-Up with Tavily

Add natural-language time parsing, recurring rules, durable scheduler recovery, Running-up states, Tavily search provenance, result deduplication, budgets, retries, user questions, completion conditions, and Telegram follow-up notifications.

Exit evidence: deterministic reminders fire once, while a Running-up item can check the web, update evidence, ask the user, and durably schedule its next step.

## Milestone 7: Operational Hardening and MVP Release

Add HTTPS deployment, rate and cost limits, structured logging, metrics, backup/restore automation, 30-day recycle retention, seven daily/four weekly backup retention, failure drills, complete acceptance tests, and deployment documentation.

Exit evidence: every acceptance criterion in the approved design is demonstrated on the deployed cloud server, including a successful restore drill.

## Approved-Spec Coverage

| Design area | Delivery milestone |
| --- | --- |
| Product principles, immutable raw layer, single-account boundary | 1 |
| Settings, encrypted credentials, Telegram account binding, future BYOK ownership | 2 |
| Canonical notes, memory books, Dashboard workspace, versions, undo, recycle bin | 3 |
| Karpathy-style compounding wiki, Agent Schema, pages, claims, edges, retrieval, lint | 4 |
| Voice, handwriting, images, documents, video, real-time sessions | 5 |
| Scheduled tasks, Running-up state machine, Tavily provenance and budgets | 6 |
| Security limits, backups, restore, fault testing, complete acceptance criteria | 7 |

No approved design section is intentionally dropped; features outside the MVP remain excluded as stated in the design specification.
