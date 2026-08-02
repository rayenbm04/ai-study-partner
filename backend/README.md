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

**Auth + Subjects** — register/login/refresh with JWT access + refresh tokens, subjects as the top-level per-user container everything else scopes to.

**Knowledge Base** — upload PDF/DOCX/PPTX/XLS(X)/images, extract text (with a vision-model fallback for scanned pages/images), hierarchical parent/child chunking, embed with a cloud embedder, store in pgvector, and LLM-tag chunks against a per-subject concept graph. Ingestion runs as a background task; `GET /documents/{id}` polls status (`pending → processing → ready|failed`).

**RAG Chat** — condense-question (using conversation history) → HyDE + multi-query expansion → per-variant vector search + Reciprocal Rank Fusion → LLM rerank → cited answer generation. Each technique is its own feature flag (see `.env.example`) so a slower/free-tier model can have some switched off without a code change.

**Summaries** — six document-scoped study-aid types (short, detailed, bullet points, key concepts, formula sheet, term definitions), grounded in the document's tagged concepts, cached per (document, type).

**Flashcards** — LLM-generated question/answer pairs from a document, grounded in its concepts, reviewed on an SM-2 spaced-repetition schedule (`GET /flashcards/due` is cross-subject).

**Quiz + Exam engine** — LLM-generated questions (mcq, true/false, short answer, calculation, fill-in-the-blank) from a document, grounded in its concepts. mcq/true_false/fill_blank are auto-graded by exact match; short_answer/calculation are graded by an LLM judging substantive equivalence. A quiz attempt hides `correct_answer`/`explanation` until submitted, so a student can't read the answer off the quiz or probe answers one at a time. Exams are quizzes with `kind="exam"` (duration, style, and a per-exam attempt history) rather than a separate table — they reuse the exact same attempt/grading endpoints a regular quiz would.

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

## Run the API

```bash
uvicorn app.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Run the tests

```bash
pytest
```

237 tests: unit tests use in-memory fakes for every repository (no DB, no network); most integration tests hit the real FastAPI app against an in-memory SQLite database; a small number (`test_chat_api.py`, `test_embedding_search_pgvector.py`) run against a real embedded Postgres+pgvector via `pgserver`, since SQLite can't execute pgvector's cosine-distance operator. No test ever calls a real LLM or embedding API — those are always faked in tests.

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

## API endpoint reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Get an access + refresh token pair |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET | `/api/v1/auth/me` | Current user |
| GET / POST | `/api/v1/subjects` | List / create subjects |
| PATCH / DELETE | `/api/v1/subjects/{id}` | Update / archive a subject |
| POST / GET | `/api/v1/subjects/{id}/documents` | Upload / list documents |
| GET / DELETE | `/api/v1/documents/{id}` | Get status / delete a document |
| POST | `/api/v1/subjects/{id}/chat` | Send a chat message (RAG) |
| GET | `/api/v1/subjects/{id}/conversations` | List conversations |
| GET | `/api/v1/conversations/{id}/messages` | List messages in a conversation |
| POST | `/api/v1/subjects/{id}/summaries` | Generate a summary |
| GET | `/api/v1/documents/{id}/summary?summary_type=...` | Get a cached summary |
| POST | `/api/v1/subjects/{id}/flashcards/generate` | Generate flashcards |
| GET | `/api/v1/subjects/{id}/flashcards` | List a subject's flashcards + review state |
| GET | `/api/v1/flashcards/due` | Cards due for review (cross-subject) |
| POST | `/api/v1/flashcards/{id}/review` | Submit an SM-2 review (quality 0-5) |
| POST | `/api/v1/subjects/{id}/quizzes/generate` | Generate a quiz |
| GET | `/api/v1/quizzes/{id}` | Get a quiz (questions, no answers) |
| POST | `/api/v1/quizzes/{id}/attempts` | Start an attempt |
| POST | `/api/v1/quiz-attempts/{id}/answers` | Submit an answer for one question |
| POST | `/api/v1/quiz-attempts/{id}/submit` | Finalize an attempt — returns score + per-question corrections |
| POST | `/api/v1/subjects/{id}/exams/generate` | Generate an exam (a quiz with `kind="exam"`) |
| GET | `/api/v1/exams/{id}/history` | This user's past attempts at one exam |

## What's not built yet

- **Progress engine** — mastery rollup from the concept graph, weak-concept detection from repeated wrong quiz/exam answers.
- **Planning engine** — study plan generation from exam date + available time + current mastery.
- **Analytics engine** — dashboards over everything above.
- **Frontend** — still the original forked React app; a page-by-page TypeScript rewrite is planned as each page is touched.
