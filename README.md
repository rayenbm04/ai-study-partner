# AI Study Coach — Backend

Clean-architecture FastAPI backend for AI Study Coach: a multi-subject, persistent-learning-model study platform, redesigned from the forked `rag-assistant` project (`rag-backend`/`rag-frontend`, left untouched alongside this folder during the transition). Full system design — six-engine model, database schema, API contract, rollout plan — is in `../docs/ARCHITECTURE.md`; this README covers what's actually built and how to run it.

Every LLM and embedding call in this pipeline is a cloud API — there is no local inference anywhere (no Ollama, no on-disk model weights). See `docs/LLM_PROVIDERS.md` for the free-tier provider comparison and upgrade path.

## Architecture

Layered, dependency pointing inward:

    api/            routes (thin — parse request, call a service, return a response schema)
      + pydantic schemas
    services/        business logic, framework-free, one package per engine
    domain/          entities (frozen dataclasses) + repository interfaces (ABCs) — no framework, no SQL
    repositories/     SQLAlchemy implementations of the domain repository interfaces
    infrastructure/   DB engine/session/ORM models, file storage, cloud LLM/embedding SDKs

A route never talks to a repository directly, and a service never imports SQLAlchemy or FastAPI — domain interfaces are the only thing services depend on, which is what makes them testable against in-memory fakes with no database at all. Domain exceptions (`app/core/exceptions.py`) carry their own HTTP status code and are mapped to responses by a single generic handler in `main.py`, so services never raise `HTTPException` directly.

Postgres + pgvector is the target datastore in every environment (local via `docker-compose.yml`, tests via either in-memory SQLite or a real embedded Postgres — see Testing below).

## What's implemented

### Auth + Subjects

JWT access tokens (short-lived) plus rotating opaque refresh tokens (hashed at rest with SHA-256, single-use — revoked the moment they're exchanged, and revoked on logout). Subjects are the top-level, student-owned container everything else scopes to; every other feature enforces ownership by checking `subject.user_id` (directly, or by walking up through `document → subject` etc.) before returning or mutating anything, so a route can never leak another user's data by id.

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`
- `GET /api/v1/subjects`, `POST /api/v1/subjects`, `GET /api/v1/subjects/{id}`, `PATCH /api/v1/subjects/{id}`, `DELETE /api/v1/subjects/{id}` (archive, not a hard delete)

### Knowledge Base

Upload a PDF, DOCX, PPTX, XLSX, XLS, TXT, PNG, JPG, or WEBP (`app/services/knowledge_base/`), and a background task (real work, not a stub — runs synchronously in tests via httpx's `ASGITransport`) does the rest:

1. **Extraction** (`extractors/`) — a real parser per file type (pdfplumber, python-docx, python-pptx, openpyxl/xlrd), including PDF text-encoding (ligature/CID) fixes ported from the original fork.
2. **Vision fallback** — scanned/image-only PDF pages (under a text-length threshold), images embedded in slides, and standalone image uploads all go through a vision-model call (`LLMProvider.complete_vision`) instead of being silently skipped. Same cloud LLM as everything else; no separate local OCR/vision pipeline.
3. **Chunking** (`chunking.py`) — hierarchical parent/child character-based splitting (no tokenizer, no llama-index dependency). Parent chunks (~900 chars) keep enough context for coherent concept tagging and citations; child chunks (~220 chars, 40 overlap) are what gets embedded and retrieved.
4. **Embedding** — child chunks are embedded and stored in pgvector.
5. **Concept tagging** (`concept_tagger.py`) — an LLM call matches each parent chunk against the subject's existing concept graph, proposes new concepts when the material clearly introduces one, and wires up prerequisite edges — this is what makes the "knowledge graph" more than a chat log; every feature below reads from it.

Not carried over from the original fork: PlantUML diagram parsing and its hardcoded French→English glossary. Everything else that fork's extractors did (vision OCR, image description, PDF text fixes) is reimplemented here against the new cloud-provider abstraction rather than copied as-is.

- `POST /api/v1/subjects/{id}/documents`, `GET /api/v1/subjects/{id}/documents`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`

### RAG Chat

`app/services/rag/` answers a student's question grounded in their uploaded material, with citations back to document/page/section. One chat turn:

1. **`query_rewrite.py`** — condenses a follow-up ("what about the second one?") into a standalone question using recent chat history, then (config-permitting) expands it into a HyDE hypothetical answer and a few reworded variations — one combined structured-JSON LLM call.
2. **`retriever.py`** — embeds every query variant, searches per-subject child-chunk embeddings via pgvector cosine distance, and fuses the ranked lists with Reciprocal Rank Fusion (RRF) — rewards a chunk that ranks well across *multiple* phrasings without needing raw distances (not comparable across different query embeddings) normalized by hand. Each hit's parent chunk is resolved for fuller context.
3. **`rerank.py`** — one more LLM call re-scores the fused candidates by actual relevance to the question (no local cross-encoder — stays cloud-only).
4. **`chat_service.py`** — orchestrates the above, generates a citation-annotated answer, and persists both the user's and assistant's messages.

Every technique is a flag (`rag_enable_hyde`, `rag_enable_multi_query`, `rag_enable_rerank`) so a stricter free-tier model can have some switched off with no code change.

- `POST /api/v1/subjects/{id}/chat`, `GET /api/v1/subjects/{id}/conversations`, `GET /api/v1/conversations/{id}/messages`

### Summaries

`app/services/summary_engine/summary_service.py` generates one of six document-scoped study aids: `short`, `detailed`, `bullet`, `key_concepts`, `formula_sheet`, `definitions`. Unlike chat, there's no vector retrieval here — a summary's "corpus" is exactly one document, so the source is that document's parent chunks (already-sized context windows from ingestion) concatenated in page order and capped at `summary_max_source_chars` so a huge document doesn't blow a free-tier context window. The one type that reaches into another engine is `key_concepts`, which grounds its prompt in whatever the ingestion pipeline already tagged to this document in the subject's concept graph, rather than asking the LLM to invent concept names from scratch. Each summary is cached per `(document_id, summary_type)` — generating overwrites the previous version rather than piling up history, since it's a cache of "what does this document say," not a log.

The document-source assembly logic (parent chunks → capped text blob) is shared with the flashcard generator below, in `app/services/knowledge_base/document_source.py`.

- `POST /api/v1/subjects/{id}/summaries` (body: `document_id`, `summary_type`) — generates/regenerates
- `GET /api/v1/documents/{id}/summary?summary_type=...` — reads back what's cached (404 if never generated)

### Flashcards

`app/services/flashcard_engine/` generates flashcards from a document and runs SM-2 spaced repetition on them:

- **`generator.py`** — one structured-JSON LLM call turns a document's source text into a batch of question/answer flashcards, calibrated difficulty (easy/medium/hard), each optionally linked to a concept from the subject's concept graph tagged to that document (same conservative-grounding approach as `key_concepts` summaries — a concept name that doesn't match the graph is dropped, not invented).
- **`sm2.py`** — the unmodified SM-2 algorithm (SuperMemo-2, 1987): pure functions, no I/O, fully unit-tested. A review is graded 0-5 ("how well did you recall this"); 0-2 is a lapse (streak resets, card comes back tomorrow), 3-5 grows the interval (1 day → 6 days → `previous_interval × ease_factor`).
- **`flashcard_service.py`** — ownership checks, generation persistence, and the review loop. A card's SM-2 state (`flashcard_reviews`, one row per `(flashcard_id, user_id)`) is created lazily on first review — a never-reviewed card is simply "due now," so there's nothing to seed at generation time.

- `POST /api/v1/subjects/{id}/flashcards/generate` (body: `document_id`, optional `count`)
- `GET /api/v1/subjects/{id}/flashcards` — every card in a subject, with each student's current SM-2 state attached if it exists
- `POST /api/v1/flashcards/{id}/review` (body: `quality`, 0-5)
- `GET /api/v1/flashcards/due` — every card across every subject this student owns that's due now (never reviewed, or past its `next_review_date`) — not subject-scoped, since "what should I study today" spans subjects

## Setup

    python3.12 -m venv .venv
    source .venv/bin/activate        # .venv\Scripts\activate on Windows
    python -m pip install -r requirements.txt
    cp .env.example .env             # fill in a real SECRET_KEY and at least one LLM_PROVIDER's API key

## Run the database migrations

Requires a running Postgres with the `pgvector` extension available (the `pgvector/pgvector:pg16` Docker image already includes it — see `docker-compose.yml`; the easiest way to get everything running locally is `docker compose up`, which starts Postgres and applies migrations automatically).

    python -m alembic upgrade head

Five migrations, applied in order:

| Migration | Adds |
|---|---|
| `0001_initial` | `users`, `subjects`, `refresh_tokens` |
| `0002_knowledge_base` | `documents`, `chunks`, `embeddings` (pgvector), `concepts`, `concept_prerequisites`, `concept_chunks`; enables the `vector` extension |
| `0003_chat` | `conversations`, `messages` |
| `0004_summaries` | `summaries` |
| `0005_flashcards` | `flashcards`, `flashcard_reviews` |

## Run the API

    python -m uvicorn app.main:app --reload

Interactive docs at `http://localhost:8000/docs`.

## Run the tests

    python -m pytest

187 tests. Almost none of them call a real LLM/embedding API or need Postgres running:

- **Unit tests** (`tests/unit/`) exercise every service (`AuthService`, `SubjectService`, `DocumentService`, `ConceptTagger`, `IngestionPipeline`, `query_rewrite`/`retriever`/`rerank`/`ChatService`, `SummaryService`, `sm2`/flashcard `generator`/`FlashcardService`) against in-memory fake repositories and providers (`tests/unit/fakes.py`) — no database, no network, no event loop surprises.
- **Extractor tests** run the real PDF/DOCX/PPTX/XLSX parsers against small files generated on the fly (a real `reportlab`-generated PDF, a real `python-docx` document, a real `python-pptx` deck with an embedded image, etc. — not mocks), with vision-model calls (scanned pages, slide images, standalone images) swapped for a fake that still exercises the real image-rendering/extraction code path.
- **Integration tests** (`tests/integration/`) hit the real FastAPI app end to end via httpx's `AsyncClient` + `ASGITransport`, against an in-memory SQLite database, covering the full upload → extract → chunk → embed → concept-tag pipeline, chat, summaries, and flashcards.
- **The one exception:** `test_embedding_search_pgvector.py` and `test_chat_api.py` run against a **real embedded Postgres+pgvector** instead of SQLite (via the `pgserver` pip package — no docker/root needed), because pgvector's cosine-distance operator (`<=>`) genuinely doesn't exist on SQLite and mocking that query wouldn't prove anything. See the `pg_server`/`pg_engine`/`pg_client` fixtures in `tests/conftest.py`.

## LLM configuration

All LLM and embedding calls are cloud APIs — nothing runs locally. See `../docs/LLM_PROVIDERS.md` for the provider comparison and rationale. Defaults to Gemini for both chat (concept tagging, chat's condense/expand/rerank/answer calls, summary and flashcard generation) and embeddings. Groq, OpenRouter, and OpenAI are implemented behind the same `LLMProvider` interface (`app/services/llm/`) — switching is a `.env` change (`LLM_PROVIDER=groq`, etc.), not a code change.

Feature-specific tuning lives in `app/core/config.py` and is `.env`-overridable — see `.env.example` for the full list:

- **RAG chat:** `RAG_ENABLE_HYDE`, `RAG_ENABLE_MULTI_QUERY`, `RAG_ENABLE_RERANK`, `RAG_RETRIEVAL_TOP_K`, `RAG_FINAL_CONTEXT_CHUNKS`, etc. — a stricter free-tier quota can turn off the extra LLM calls (HyDE, multi-query, rerank) without touching code.
- **Summaries:** `SUMMARY_MAX_SOURCE_CHARS`.
- **Flashcards:** `FLASHCARD_SOURCE_MAX_CHARS`, `FLASHCARD_DEFAULT_GENERATE_COUNT`, `FLASHCARD_MAX_GENERATE_COUNT`.

## API endpoint reference

All routes are prefixed `/api/v1` and (except auth) require `Authorization: Bearer <access_token>`.

| Method & path | Purpose |
|---|---|
| `POST /auth/register` | Create an account |
| `POST /auth/login` | Get an access + refresh token pair |
| `POST /auth/refresh` | Rotate a refresh token for a new pair |
| `POST /auth/logout` | Revoke a refresh token |
| `GET /auth/me` | Current user |
| `GET /subjects` | List your subjects |
| `POST /subjects` | Create a subject |
| `GET /subjects/{id}` | Get a subject |
| `PATCH /subjects/{id}` | Update a subject |
| `DELETE /subjects/{id}` | Archive a subject |
| `POST /subjects/{id}/documents` | Upload + ingest a document |
| `GET /subjects/{id}/documents` | List a subject's documents |
| `GET /documents/{id}` | Get a document (status, page count) |
| `DELETE /documents/{id}` | Delete a document |
| `POST /subjects/{id}/chat` | Ask a question, grounded in the subject's material |
| `GET /subjects/{id}/conversations` | List a subject's chat conversations |
| `GET /conversations/{id}/messages` | A conversation's message history |
| `POST /subjects/{id}/summaries` | Generate/regenerate a document summary |
| `GET /documents/{id}/summary` | Read a cached summary (`?summary_type=`) |
| `POST /subjects/{id}/flashcards/generate` | Generate flashcards from a document |
| `GET /subjects/{id}/flashcards` | List a subject's flashcards (+ your review state) |
| `POST /flashcards/{id}/review` | Grade a review (SM-2) |
| `GET /flashcards/due` | Every card due for review, across subjects |

## What's not built yet

Per `../docs/ARCHITECTURE.md`'s rollout plan: Quiz + Exam engine, Progress engine (mastery rollup, weak-concept detection), Planning engine (study plans/scheduling), Analytics, and the frontend migration. Nothing above depends on those being built first.
