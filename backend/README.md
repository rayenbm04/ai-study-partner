# AI Study Coach — Backend (Phase 3: Knowledge Base)

Clean-architecture FastAPI backend. See `../docs/ARCHITECTURE.md` for the full
system design; this covers only what's implemented so far.

## What's here

- **Auth (Phase 2):** JWT access tokens + rotating opaque refresh tokens (hashed at
  rest, revoked on use/logout).
- **Subjects (Phase 2):** student-owned, multi-subject, ownership-enforced on every route.
- **Knowledge Base (Phase 3):** upload a PDF/DOCX/PPTX/XLSX/TXT, and a background task
  extracts text, splits it into parent/child chunks, embeds the child chunks, and tags
  the parent chunks against a per-subject concept graph (creating concepts and
  prerequisite edges as needed) — see `app/services/knowledge_base/`.
- Layered: `api/` (routes + pydantic schemas) → `services/` (business rules, framework-free)
  → `domain/` (entities + repository interfaces) → `repositories/` (SQLAlchemy impls)
  → `infrastructure/` (db engine/session/ORM models, file storage, cloud LLM/embedding SDKs).
- Postgres + pgvector target in production; tests run against in-memory SQLite (pgvector's
  `Vector` column type works fine there for structural testing) via a swapped `get_db`
  dependency, and unit tests run against in-memory fakes with no DB at all.
- Standalone images and scanned-only PDFs aren't supported yet — that needs a vision LLM
  call per page and is a deliberately separate increment, not a stub in this codebase.

## Setup

    python3.12 -m venv .venv
    source .venv/bin/activate        # .venv\Scripts\activate on Windows
    python -m pip install -r requirements.txt
    cp .env.example .env             # fill in a real SECRET_KEY and DATABASE_URL

## Run the database migrations

Requires a running Postgres — migration `0002` runs `CREATE EXTENSION IF NOT EXISTS vector`
itself, so you don't need to enable pgvector by hand, just have it installed on the server
(the `pgvector/pgvector:pg16` Docker image already includes it — see `docker-compose.yml`):

    python -m alembic upgrade head

## Run the API

    python -m uvicorn app.main:app --reload

Docs at `http://localhost:8000/docs`.

## Run the tests

    python -m pytest

74 tests, none of which call a real LLM or embedding API or need Postgres running:
unit tests exercise services (`AuthService`, `SubjectService`, `DocumentService`,
`ConceptTagger`, `IngestionPipeline`) against in-memory fake repositories/providers;
extractor tests run the real PDF/DOCX/PPTX/XLSX parsers against small files generated
on the fly (a real `reportlab`-generated PDF, a real `python-docx` document, etc. —
not mocks); integration tests hit the real FastAPI app end to end, including a full
upload → extract → chunk → embed → concept-tag run, against an in-memory SQLite
database with the LLM and embedder swapped for deterministic fakes.

## LLM configuration

All LLM and embedding calls are cloud APIs — nothing runs locally. See
`../docs/LLM_PROVIDERS.md` for the provider comparison and rationale. Defaults to Gemini
for both chat (concept tagging now; tutoring/summaries/quizzes from Phase 4 onward) and
embeddings. Groq, OpenRouter, and OpenAI are implemented behind the same `LLMProvider`
interface (`app/services/llm/`) — switching is a `.env` change (`LLM_PROVIDER=groq`, etc.),
not a code change.
