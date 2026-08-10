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

**Auth + Subjects** — register/login/refresh with JWT access + refresh tokens. Registration collects a student profile (pseudo/username, date of birth, optional school name) in addition to name/email/password, with confirm-password matching and a lightweight weak-password check (`app/core/security.py:weak_password_reason`) — no email verification or password-reset flow yet (columns exist on `users` for both, unused until an email-sending service is wired up). Subjects are the top-level per-user container everything else scopes to.

**Curriculum + Subject Packs** — a shared, global reference catalog (`Country → EducationSystem → AcademicLevel → Section → CurriculumSubject → Chapter → Lesson`) browsable read-only by any authenticated user. A student can either link an individual subject to a `CurriculumSubject` node (`PATCH /subjects/{id}`) or bulk-apply every subject under an academic level/section as a "pack" (`POST /subject-packs/apply`) — the pack itself isn't a stored entity, just a bulk-create against the same catalog. `PATCH /account/classe` separately remembers a student's own academic level/section on their profile (distinct from applying a pack, which only decides *which subjects get added*).

**Account** — `POST /account/reset` wipes a user's subjects/documents/study plans (and everything that cascades from them) without touching the login itself; `PATCH /account/classe` sets or clears the student's own academic level/section, validated against the curriculum catalog.

**Knowledge Base** — upload PDF/DOCX/PPTX/XLS(X)/images, extract text (with a vision-model fallback for scanned pages/images), hierarchical parent/child chunking, embed with a cloud embedder, store in pgvector, and LLM-tag chunks against a per-subject concept graph. Ingestion runs as a background task; `GET /documents/{id}` polls status (`pending → processing → ready|failed`).

**RAG Chat** — condense-question (using conversation history) → HyDE + multi-query expansion → per-variant vector search + Reciprocal Rank Fusion → LLM rerank → cited answer generation. Each technique is its own feature flag (see `.env.example`) so a slower/free-tier model can have some switched off without a code change. An optional `document_id` on the chat request narrows retrieval to one document instead of the whole subject, for "ask about this upload" style questions.

**Summaries** — six document-scoped study-aid types (short, detailed, bullet points, key concepts, formula sheet, term definitions), grounded in the document's tagged concepts, cached per (document, type).

**Flashcards** — LLM-generated question/answer pairs from a document, grounded in its concepts, reviewed on an SM-2 spaced-repetition schedule (`GET /flashcards/due` is cross-subject).

**Quiz + Exam engine** — LLM-generated questions (mcq, true/false, short answer, calculation, fill-in-the-blank) from a document, grounded in its concepts. mcq/true_false/fill_blank are auto-graded by exact match; short_answer/calculation are graded by an LLM judging substantive equivalence. A quiz attempt hides `correct_answer`/`explanation` until submitted, so a student can't read the answer off the quiz or probe answers one at a time. Exams are quizzes with `kind="exam"` (duration, style, and a per-exam attempt history) rather than a separate table — they reuse the exact same attempt/grading endpoints a regular quiz would.

**Progress engine** — recomputes, on every read, a 0-100 mastery score per concept from whatever evidence exists for it (latest flashcard review grade + quiz/exam answer correctness), rolls it up the concept tree (chapter/subject mastery is never stored, just aggregated from children), and flags weak concepts from three signals: `repeated_errors` (a high wrong-answer rate), `slow_response` (answers taking much longer than a baseline), and `decay` (a previously-mastered concept whose score has since dropped). No LLM calls — purely arithmetic over data the other engines already record. Thresholds are `.env`-tunable (see below), not hardcoded, since they're heuristics rather than a fixed spec.

**Planning engine** — generates a day-by-day study plan across one or more subjects: ranks concepts by urgency (weak-flagged and never-touched concepts first, then ascending mastery score, reusing the progress engine's own scoring), then distributes sessions across days based on `daily_minutes_available` and an optional `exam_date` (defaulting to a 14-day plan if no exam date is given), reserving the final day before an exam date for a full-subject review session. No LLM calls, no new tracking tables — a plan item's status (pending/done/skipped) is set explicitly by the student rather than auto-logged from activity elsewhere.

**Analytics engine** — read-side aggregation only, per the architecture doc's "no new tables" directive: per-subject and cross-subject overview stats (documents, flashcards + due count, quizzes/exams + average score, conversations, average mastery, weak-concept count, concepts practiced vs. total) computed on request from data the other five engines already store.

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
| `0011` | `users`: `date_of_birth`, `pseudo` (unique), `school_name`, `academic_level_id`/`section_id` (a student's own classe), `is_verified`/`email_verified_at` (unused until email verification is built) |

## Run the API

```bash
uvicorn app.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Run the tests

```bash
pytest
```

409 tests: unit tests use in-memory fakes for every repository (no DB, no network); most integration tests hit the real FastAPI app against an in-memory SQLite database; a small number (`test_chat_api.py`, `test_embedding_search_pgvector.py`, and one deep test each in `test_progress_api.py` and `test_study_plans_api.py`) run against a real embedded Postgres+pgvector via `pgserver`. No test ever calls a real LLM or embedding API — those are always faked in tests.

## LLM configuration

Every LLM/embedding call goes through a provider interface (`services/llm/base.py`, `services/embeddings/base.py`) — swapping providers is a `.env` change, never a code change. See [`../docs/LLM_PROVIDERS.md`](../docs/LLM_PROVIDERS.md) for the free-tier comparison.

| Setting | Purpose |
|---|---|
| `LLM_PROVIDER` | `gemini` \| `groq` \| `openrouter` \| `openai` |
| `EMBEDDING_PROVIDER` | `gemini` (only option for now) |
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

## API endpoint reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account (name, email, password, pseudo, date of birth, optional school) |
| POST | `/api/v1/auth/login` | Get an access + refresh token pair |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/account/reset` | Wipe this user's subjects/documents/study plans (keeps the login) |
| PATCH | `/api/v1/account/classe` | Set or clear the student's own academic level/section |
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

- **Email verification / password reset** — `users.is_verified`/`email_verified_at` columns exist for a future confirmation flow, but nothing sends real email yet; registration doesn't block on verification.
- **School catalog** — `school_name` is free text; no dedicated school entity/catalog.
- See [`mobile/README.md`](../mobile/README.md) for what's built vs. pending on the client — the original forked `rag-frontend` React app is no longer the active frontend (see top-level README).
