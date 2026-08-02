# AI Study Coach — Backend (Phase 3: Knowledge Base)

Clean-architecture FastAPI backend. See `../docs/ARCHITECTURE.md` for the full
system design; this covers only what's implemented so far.

## What's here

- **Auth (Phase 2):** JWT access tokens + rotating opaque refresh tokens (hashed at
  rest, revoked on use/logout).
- **Subjects (Phase 2):** student-owned, multi-subject, ownership-enforced on every route.
- **Knowledge Base (Phase 3):** upload a PDF/DOCX/PPTX/XLSX/XLS/TXT/PNG/JPG/WEBP, and a
  background task extracts text, splits it into parent/child chunks, embeds the child
  chunks, and tags the parent chunks against a per-subject concept graph (creating
  concepts and prerequisite edges as needed) — see `app/services/knowledge_base/`.
  Scanned/image-only PDF pages, images embedded in slides, and standalone image uploads
  all go through a vision-model call (`LLMProvider.complete_vision`) rather than being
  silently skipped — same cloud LLM as everything else, no separate vision pipeline.
- Layered: `api/` (routes + pydantic schemas) → `services/` (business rules, framework-free)
  → `domain/` (entities + repository interfaces) → `repositories/` (SQLAlchemy impls)
  → `infrastructure/` (db engine/session/ORM models, file storage, cloud LLM/embedding SDKs).
- Postgres + pgvector target in production; tests run against in-memory SQLite (pgvector's
  `Vector` column type works fine there for structural testing) via a swapped `get_db`
  dependency, and unit tests run against in-memory fakes with no DB at all.
- Not carried over from the original rag-backend fork: PlantUML diagram parsing and its
  hardcoded French→English glossary. Everything else that fork's extractors did (vision
  OCR fallback, image description, PDF text encoding fixes) is now here, reimplemented
  against the new provider abstraction rather than copied as-is.

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

84 tests, none of which call a real LLM or embedding API or need Postgres running:
unit tests exercise services (`AuthService`, `SubjectService`, `DocumentService`,
`ConceptTagger`, `IngestionPipeline`) against in-memory fake repositories/providers;
extractor tests run the real PDF/DOCX/PPTX/XLSX parsers against small files generated
on the fly (a real `reportlab`-generated PDF, a real `python-docx` document, a real
`python-pptx` deck with an embedded image, etc. — not mocks), with the vision-model
calls (scanned PDF pages, slide images, standalone images) swapped for a fake that still
exercises the real image-rendering/extraction code path; integration tests hit the real
FastAPI app end to end, including a full upload → extract → chunk → embed → concept-tag
run for both a text document and an image, against an in-memory SQLite database.

If you already had `backend/.venv` from Phase 2, re-run `pip install -r requirements.txt`
— this phase added `google-genai`, `openai`, `pdfplumber`, `python-docx`, `python-pptx`,
`openpyxl`, `xlrd`, `pillow`, and `reportlab` (test-only).

## LLM configuration

All LLM and embedding calls are cloud APIs — nothing runs locally. See
`../docs/LLM_PROVIDERS.md` for the provider comparison and rationale. Defaults to Gemini
for both chat (concept tagging now; tutoring/summaries/quizzes from Phase 4 onward) and
embeddings. Groq, OpenRouter, and OpenAI are implemented behind the same `LLMProvider`
interface (`app/services/llm/`) — switching is a `.env` change (`LLM_PROVIDER=groq`, etc.),
not a code change.
