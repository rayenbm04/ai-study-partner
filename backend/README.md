# AI Study Coach — Backend

FastAPI backend for the AI Study Coach platform (see the [top-level README](../README.md) for the product vision). Clean/layered architecture, PostgreSQL + pgvector, cloud-only LLMs. Full design doc: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Architecture

```
api/v1/          FastAPI routes + pydantic schemas — thin, no business logic
services/        business logic, one package per engine
domain/          framework-free entities + repository interfaces (ports)
repositories/     SQLAlchemy implementations of those ports
infrastructure/  DB session/models, storage, vector store
core/            settings, security, domain exceptions
```

Routes depend on services, services depend on repository *interfaces* (never on SQLAlchemy directly), and `api/v1/deps.py` wires the concrete implementations in. Services raise `DomainError` subclasses (`app/core/exceptions.py`) instead of `HTTPException`; a single handler in `main.py` maps them to HTTP responses, so business logic stays testable without spinning up FastAPI.

## What's implemented

**Auth + Subjects** — register/login/refresh with JWT access + refresh tokens. Registration collects a student profile (pseudo/username, date of birth, optional school) in addition to name/email/password, with confirm-password matching and a lightweight weak-password check (`app/core/security.py:weak_password_reason`). Login is rate-limited (`AuthService.authenticate`): after `LOGIN_MAX_FAILED_ATTEMPTS` wrong passwords the account is locked for `LOGIN_LOCKOUT_MINUTES` (a `423 Locked` response), reset on the next successful login. Email verification and password reset are both wired up end to end (tokens, expiry, single-use, `POST /auth/verify-email` / `POST /auth/forgot-password` / `POST /auth/reset-password`) but delivery is stubbed — see **Email** below. Every register/login/lockout/verification/reset event is appended to `security_events` (`app/domain/repositories/security_event_repository.py`) — an audit trail, not read by anything yet. Subjects are the top-level per-user container everything else scopes to.

**Schools** — a small institution catalog (`schools`, `school_classes`) a student searches or adds their school against at registration (`GET/POST /api/v1/schools`, `GET/POST /api/v1/schools/{id}/classes`) — replaces an earlier free-text `school_name` field. These routes are deliberately public (no auth): a student needs to search for/add their school *during* the registration form, before an account exists to authenticate with, the same trade-off `POST /auth/register` itself makes. There's no admin gate on `POST /schools` yet — anyone can add an entry, matching this codebase's current scope (no abuse protection anywhere else either). Distinct from the curriculum catalog below: a School is *which institution*; `school_classes` is that institution's own class list, kept separate from — and not wired into — the curriculum-based "classe" a student picks via `PATCH /account/classe`.

**Curriculum + Subject Packs** — a shared, global reference catalog (`Country → EducationSystem → AcademicLevel → Section → CurriculumSubject → Chapter → Lesson`) browsable read-only by any authenticated user. A student can either link an individual subject to a `CurriculumSubject` node (`PATCH /subjects/{id}`) or bulk-apply every subject under an academic level/section as a "pack" (`POST /subject-packs/apply`) — the pack itself isn't a stored entity, just a bulk-create against the same catalog. `PATCH /account/classe` separately remembers a student's own academic level/section on their profile (distinct from applying a pack, which only decides *which subjects get added*).

**Account** — `POST /account/reset` wipes a user's subjects/documents/study plans (and everything that cascades from them) without touching the login itself; `PATCH /account/classe` sets or clears the student's own academic level/section, validated against the curriculum catalog.

**Email** — every verification/reset email goes through an `EmailSender` interface (`app/services/email/base.py`), same "interface first, swap the implementation" pattern as `LLMProvider`. Only implementation today is `LoggingEmailSender` (`EMAIL_SENDER=logging`, the default) — it logs the full email body (including the token) to the server console instead of sending it, so registering or requesting a password reset locally means checking the terminal output for the code rather than an inbox. Wiring up a real provider (Resend, SendGrid, SES, ...) later is a new `EmailSender` implementation registered in `app/services/email/factory.py`, not a change to `AuthService`.

**Knowledge Base** — upload PDF/DOCX/PPTX/XLS(X)/images, extract text (with a vision-model fallback for scanned pages/images), hierarchical parent/child chunking, embed with a cloud embedder, store in pgvector, and LLM-tag chunks against a per-subject concept graph. Ingestion runs as a background task; `GET /documents/{id}` polls status (`pending → processing → ready|failed`), and while `processing` the response also carries `processing_step` (`extracting` → `chunking` → `embedding` → `classifying`) and a `processing_progress` percentage for a granular upload UI. A byte-identical re-upload to the same subject (sha256 of the raw content, `documents.content_hash`) returns the existing document instead of reprocessing it (`document_dedup_enabled`, on by default) — no extra embedding/LLM spend on accidental duplicate uploads. `IngestionPipeline.run()` commits the document as `ready` (and usable for RAG chat) as soon as extraction/chunking/embedding/classification are done; concept tagging (`tag_concepts()`, the knowledge-graph enrichment behind progress/planning) runs afterward as a best-effort follow-up in its own transaction, so a tagging failure never un-readies an already-indexed document.

**RAG Chat** — condense-question (using conversation history) → HyDE + multi-query expansion → per-variant vector search + Reciprocal Rank Fusion → LLM rerank → cited answer generation. Each technique is its own feature flag (see `.env.example`) so a slower/free-tier model can have some switched off without a code change. An optional `document_id` on the chat request narrows retrieval to one document instead of the whole subject, for "ask about this upload" style questions. Full step-by-step walkthrough of both ingestion and retrieval, accurate to the current code: [`../docs/RAG_PIPELINE.md`](../docs/RAG_PIPELINE.md).

**Summaries** — six document-scoped study-aid types (short, detailed, bullet points, key concepts, formula sheet, term definitions), grounded in the document's tagged concepts, cached per (document, type).

**Flashcards** — LLM-generated question/answer pairs from a document, grounded in its concepts, reviewed on an SM-2 spaced-repetition schedule (`GET /flashcards/due` is cross-subject).

**Quiz + Exam engine** — LLM-generated questions (mcq, true/false, short answer, calculation, fill-in-the-blank) from a document, grounded in its concepts. mcq/true_false/fill_blank are auto-graded by exact match; short_answer/calculation are graded by an LLM judging substantive equivalence. A quiz attempt hides `correct_answer`/`explanation` until submitted, so a student can't read the answer off the quiz or probe answers one at a time. Exams are quizzes with `kind="exam"` (duration, style, and a per-exam attempt history) rather than a separate table — they reuse the exact same attempt/grading endpoints a regular quiz would.

**Progress engine** — recomputes, on every read, a 0-100 mastery score per concept from whatever evidence exists for it (latest flashcard review grade + quiz/exam answer correctness), rolls it up the concept tree (chapter/subject mastery is never stored, just aggregated from children), and flags weak concepts from three signals: `repeated_errors` (a high wrong-answer rate), `slow_response` (answers taking much longer than a baseline), and `decay` (a previously-mastered concept whose score has since dropped). No LLM calls — purely arithmetic over data the other engines already record. Thresholds are `.env`-tunable (see below), not hardcoded, since they're heuristics rather than a fixed spec.

**Planning engine** — generates a day-by-day study plan across one or more subjects: ranks concepts by urgency (weak-flagged and never-touched concepts first, then ascending mastery score, reusing the progress engine's own scoring), then distributes sessions across days based on `daily_minutes_available` and an optional `exam_date` (defaulting to a 14-day plan if no exam date is given), reserving the final day before an exam date for a full-subject review session. No LLM calls, no new tracking tables — a plan item's status (pending/done/skipped) is set explicitly by the student rather than auto-logged from activity elsewhere.

**Analytics engine** — read-side aggregation only, per the architecture doc's "no new tables" directive: per-subject and cross-subject overview stats (documents, flashcards + due count, quizzes/exams + average score, conversations, average mastery, weak-concept count, concepts practiced vs. total) computed on request from data the other five engines already store.

**Usage tracking** — `UsageService` logs a `usage_events` row (`app/domain/entities/usage_event.py`) for every document upload and every AI request (chat, summary, flashcard, quiz generation), per user — this is architecture for a future free/premium tier, not a paywall today: the backend runs on one shared provider API key, so `usage_events` is currently the only place per-user consumption is visible at all. Limit *enforcement* is gated behind `usage_limits_enabled` (default `False`), so nothing is rate-limited yet; flipping it on (once tiers actually exist) makes `UsageService.check_ai_request_limit`/`check_document_limit` start raising `UsageLimitExceededError` against `free_daily_ai_requests`/`free_daily_documents`, no code change needed. Nothing surfaces this via an API endpoint yet — same "logged, not read by anything" state as `security_events` (see Auth above).

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in at least one LLM provider API key
```

Postgres with the `pgvector` extension is required (see `docker-compose.yml` for a local one, or point `DATABASE_URL` at any Postgres 15+ instance with `CREATE EXTENSION vector` run once).

## Run the database migrations

```bash
alembic upgrade head
```

| Revision | Adds |
|---|---|
| `0001` | `users`, `subjects`, `refresh_tokens` |
| `0002` | `documents`, `chunks`, `embeddings` (pgvector), `concepts`, `concept_prerequisites`, `concept_chunks` |
| `0003` | `conversations`, `messages` |
| `0004` | `summaries` |
| `0005` | `flashcards`, `flashcard_reviews` |
| `0006` | `quizzes`, `quiz_questions`, `quiz_attempts`, `student_answers` |
| `0007` | `progress`, `weak_concepts` |
| `0008` | `study_plans`, `study_plan_items` |
| `0009` | curriculum catalog (`curriculum_countries`, `curriculum_education_systems`, `curriculum_academic_levels`, `curriculum_sections`, `curriculum_subjects`, `curriculum_chapters`, `curriculum_lessons`) + `subjects.curriculum_subject_id` + document classification columns |
| `0010` | scopes `subjects`' `(user_id, name)` uniqueness to active (non-archived) subjects only, via a partial unique index |
| `0011` | `users`: `date_of_birth`, `pseudo` (unique), `school_name`, `academic_level_id`/`section_id` (a student's own classe), `is_verified`/`email_verified_at` |
| `0012` | `schools`, `school_classes`, `verification_tokens` (email verification / password reset), `security_events`; `users`: `school_name` → `school_id` (FK to `schools`), `status`, `last_login_at`, `failed_login_attempts`, `locked_until` (login-attempt limiting) |
| `0013` | `documents`: `content_hash` (upload dedup, indexed), `processing_step`/`processing_progress` (granular ingestion status); `usage_events` (per-user AI/document usage log — see Usage tracking above) |

## Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0
```

`--host 0.0.0.0` is required, not optional — uvicorn's default (`127.0.0.1`) only accepts
connections from the same machine, so the mobile app's LAN-IP `EXPO_PUBLIC_API_URL`
(needed for physical devices / Expo Go, see `mobile/.env`) can't reach it and requests
fail before ever reaching this process (nothing logged, no server-side error).

Interactive docs at `http://127.0.0.1:8000/docs`.

## Run the tests

```bash
pytest
```

443 tests: unit tests use in-memory fakes for every repository (no DB, no network); most integration tests hit the real FastAPI app against an in-memory SQLite database; a small number (`test_chat_api.py`, `test_embedding_search_pgvector.py`, and one deep test each in `test_progress_api.py` and `test_study_plans_api.py`) run against a real embedded Postgres+pgvector via `pgserver`. No test ever calls a real LLM or embedding API — those are always faked in tests, and no test ever sends a real email (`LoggingEmailSender`/`FakeEmailSender` never touch the network either).

`app/infrastructure/db/session.py`'s `get_db()` commits on a `DomainError` (not just on success) rather than rolling it back — a `DomainError` is a business-rule 4xx response, not a corrupt transaction, and some flows deliberately write *then* raise one in the same request (e.g. `AuthService.authenticate` records a failed-login attempt, then raises `InvalidCredentialsError`; that write has to survive or the lockout counter would never accumulate). `tests/conftest.py`'s `override_get_db` mirrors this exactly — worth knowing if a future test writes something before a service raises a `DomainError` and expects that write to have happened.

## LLM configuration

Every LLM/embedding call goes through a provider interface (`services/llm/base.py`, `services/embeddings/base.py`) — swapping providers is a `.env` change, never a code change. See [`../docs/LLM_PROVIDERS.md`](../docs/LLM_PROVIDERS.md) for the free-tier comparison.

Each provider is actually two model tiers behind the same interface (`services/llm/factory.py`): `build_llm_provider` (the main/"complex" model — tutoring answers, exam-question grading, anything needing real reasoning) and `build_simple_llm_provider` (a cheaper/faster model for mechanical, high-volume calls — concept tagging, document classification, summaries, flashcard/quiz generation, RAG query rewriting). The `*_simple_chat_model` settings below default to `""`, which falls back to that provider's main chat model — Groq and Cerebras both ship a safe default (`openai/gpt-oss-20b`, `llama3.1-8b`); Gemini/OpenRouter/OpenAI are left blank since guessing a stable "lite" model name isn't safe (model names on the cheap tiers churn fastest).

**Cerebras + automatic fallback**: `LLM_FALLBACK_PROVIDER` (empty by default — no behavior change until set) wraps `LLM_PROVIDER` in a `FallbackLLMProvider` (`services/llm/fallback_provider.py`) that retries against a second provider whenever the first is rate-limited, or — Cerebras-specific, since its current lineup has no vision-capable model — whenever a vision call would fail outright. `LLM_PROVIDER=cerebras` + `LLM_FALLBACK_PROVIDER=groq` is the combination this was built for: Cerebras' free tier (30 req/min, 14.4K req/day, 1M tokens/day on `gpt-oss-120b`, no card) is generous enough to be the primary, with Groq catching both 429s and every vision call. See [`../docs/LLM_PROVIDERS.md`](../docs/LLM_PROVIDERS.md) for the full comparison and routing diagram.

| Setting | Purpose |
|---|---|
| `LLM_PROVIDER` | `gemini` \| `groq` \| `cerebras` \| `openrouter` \| `openai` |
| `LLM_FALLBACK_PROVIDER` | second provider to retry against on a rate limit or missing vision support; empty (default) = no fallback |
| `EMBEDDING_PROVIDER` | `gemini` \| `local` (CPU `sentence-transformers`, no key/card — see `docs/LLM_PROVIDERS.md`) |
| `GEMINI_SIMPLE_CHAT_MODEL` / `GROQ_SIMPLE_CHAT_MODEL` / `CEREBRAS_SIMPLE_CHAT_MODEL` / `OPENROUTER_SIMPLE_CHAT_MODEL` / `OPENAI_SIMPLE_CHAT_MODEL` | cheap-tier model for mechanical calls; empty = reuse that provider's main chat model |
| `DOCUMENT_DEDUP_ENABLED` | skip reprocessing a byte-identical re-upload to the same subject (default `True`) |
| `USAGE_LIMITS_ENABLED` | enforce the daily limits below instead of just logging usage (default `False`, no tiers exist yet) |
| `FREE_DAILY_AI_REQUESTS` / `FREE_DAILY_DOCUMENTS` | daily per-user caps once `USAGE_LIMITS_ENABLED=True` |
| `RAG_ENABLE_HYDE` / `RAG_ENABLE_MULTI_QUERY` / `RAG_ENABLE_RERANK` | toggle each RAG technique independently |
| `RAG_RETRIEVAL_TOP_K` / `RAG_FINAL_CONTEXT_CHUNKS` / `RAG_HISTORY_MESSAGES` | RAG chat tuning |
| `SUMMARY_MAX_SOURCE_CHARS` | cap on source text fed into a summary call |
| `FLASHCARD_SOURCE_MAX_CHARS` / `FLASHCARD_DEFAULT_GENERATE_COUNT` / `FLASHCARD_MAX_GENERATE_COUNT` | flashcard generation tuning |
| `QUIZ_SOURCE_MAX_CHARS` / `QUIZ_DEFAULT_GENERATE_COUNT` / `QUIZ_MAX_GENERATE_COUNT` | quiz/exam generation tuning |
| `PROGRESS_TREND_UP_THRESHOLD` / `PROGRESS_TREND_DOWN_THRESHOLD` | minimum point change to call a concept's trend up/down instead of flat |
| `WEAK_CONCEPT_MIN_ERROR_COUNT` / `WEAK_CONCEPT_ERROR_RATE_THRESHOLD` | repeated-errors detection tuning |
| `WEAK_CONCEPT_SLOW_RESPONSE_SECONDS` | slow-response baseline |
| `WEAK_CONCEPT_DECAY_DROP_THRESHOLD` / `WEAK_CONCEPT_DECAY_MIN_PREVIOUS_SCORE` | decay detection tuning |
| `PLANNING_DEFAULT_SESSION_MINUTES` / `PLANNING_DEFAULT_PLAN_DAYS` | study-plan session length and default plan length when no exam date is set |
| `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | failed logins before an account locks, and how long the lock lasts |
| `EMAIL_SENDER` | `logging` (only option today — see the Email section above) |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` / `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | how long a verify-email / reset-password code stays valid |

## API endpoint reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account (name, email, password, pseudo, date of birth, optional `school_id`) |
| POST | `/api/v1/auth/login` | Get an access + refresh token pair (`423` if the account is locked from repeated failures) |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/auth/verify-email` | Confirm an email-verification code |
| POST | `/api/v1/auth/forgot-password` | Request a password-reset code (always `204`, doesn't reveal whether the email exists) |
| POST | `/api/v1/auth/reset-password` | Reset the password with a valid code; revokes every existing refresh token |
| POST | `/api/v1/account/reset` | Wipe this user's subjects/documents/study plans (keeps the login) |
| PATCH | `/api/v1/account/classe` | Set or clear the student's own academic level/section |
| GET | `/api/v1/schools?q=...` | Search the school catalog (public, no auth) |
| POST | `/api/v1/schools` | Add a school not found by search (public, no auth) |
| GET | `/api/v1/schools/{id}` | Get one school |
| GET / POST | `/api/v1/schools/{id}/classes` | List / add that school's own classes |
| GET | `/api/v1/curriculum/countries` | List countries |
| GET | `/api/v1/curriculum/countries/{id}/education-systems` | List education systems in a country |
| GET | `/api/v1/curriculum/education-systems/{id}/academic-levels` | List academic levels in a system |
| GET | `/api/v1/curriculum/academic-levels/{id}/sections` | List sections in a level |
| GET | `/api/v1/curriculum/academic-levels/{id}/subjects?section_id=...` | List curriculum subjects for a level (+ optional section) |
| GET | `/api/v1/curriculum/subjects/{id}/chapters` | List chapters in a curriculum subject |
| GET | `/api/v1/curriculum/chapters/{id}/lessons` | List lessons in a chapter |
| GET | `/api/v1/subject-packs` | List curriculum packs (level/section) already applied by this user |
| POST | `/api/v1/subject-packs/apply` | Bulk-create subjects for every curriculum subject under a level/section |
| POST | `/api/v1/subject-packs/remove` | Bulk-remove the subjects a previously applied pack created |
| GET / POST | `/api/v1/subjects` | List / create subjects |
| PATCH / DELETE | `/api/v1/subjects/{id}` | Update (incl. linking to a curriculum subject) / archive a subject |
| POST / GET | `/api/v1/subjects/{id}/documents` | Upload / list documents |
| GET / DELETE | `/api/v1/documents/{id}` | Get status / delete a document |
| GET | `/api/v1/documents/{id}/content` | Get a document's raw file bytes |
| POST | `/api/v1/subjects/{id}/chat` | Send a chat message (RAG); optional `document_id` narrows retrieval to one document |
| GET | `/api/v1/subjects/{id}/conversations` | List conversations |
| GET | `/api/v1/conversations/{id}/messages` | List messages in a conversation |
| POST | `/api/v1/subjects/{id}/summaries` | Generate a summary |
| GET | `/api/v1/documents/{id}/summary?summary_type=...` | Get a cached summary |
| GET | `/api/v1/documents/{id}/summaries` | List every summary type generated for a document |
| POST | `/api/v1/subjects/{id}/flashcards/generate` | Generate flashcards |
| GET | `/api/v1/subjects/{id}/flashcards` | List a subject's flashcards + review state |
| GET | `/api/v1/flashcards/due` | Cards due for review (cross-subject) |
| POST | `/api/v1/flashcards/{id}/review` | Submit an SM-2 review (quality 0-5) |
| GET | `/api/v1/subjects/{id}/quizzes` | List quizzes generated for a subject (+ question count) |
| POST | `/api/v1/subjects/{id}/quizzes/generate` | Generate a quiz |
| GET | `/api/v1/quizzes/{id}` | Get a quiz (questions, no answers) |
| POST | `/api/v1/quizzes/{id}/attempts` | Start an attempt |
| POST | `/api/v1/quiz-attempts/{id}/answers` | Submit an answer for one question |
| POST | `/api/v1/quiz-attempts/{id}/submit` | Finalize an attempt — returns score + per-question corrections |
| POST | `/api/v1/subjects/{id}/exams/generate` | Generate an exam (a quiz with `kind="exam"`) |
| GET | `/api/v1/exams/{id}/history` | This user's past attempts at one exam |
| GET | `/api/v1/subjects/{id}/progress` | Rolled-up concept-tree mastery for this subject |
| GET | `/api/v1/subjects/{id}/weak-concepts` | Currently-active detected gaps for this subject |
| POST | `/api/v1/study-plans` | Generate a study plan across one or more subjects |
| GET | `/api/v1/study-plans/{id}` | Get a plan and its scheduled items |
| PATCH | `/api/v1/study-plan-items/{id}` | Mark a plan item pending / done / skipped |
| GET | `/api/v1/analytics/overview` | Cross-subject stats (subject count, total flashcards due, per-subject breakdown) |
| GET | `/api/v1/analytics/subjects/{id}` | Stats for one subject (documents, flashcards, quizzes, mastery, weak concepts) |

## What's not built yet

- **A real email provider** — verification/reset codes are only ever logged to the server console (`EMAIL_SENDER=logging`); nothing actually reaches a student's inbox yet.
- **Login never blocks on `is_verified`** — verification is tracked and confirmable, but registration and login don't require it. Deliberate for now (no product decision yet on whether/when to enforce it).
- **No admin tooling** — `POST /schools` has no gate (see the Schools section above), and `users.status` exists but nothing ever sets it to anything but `"active"` (no suspend/ban action yet).
- See [`mobile/README.md`](../mobile/README.md) for what's built vs. pending on the client — the original forked `rag-frontend` React app is no longer the active frontend (see top-level README).
