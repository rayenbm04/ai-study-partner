# AI Study Coach — Backend (Phase 4: RAG Chat)

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
- **RAG Chat (Phase 4):** `POST /subjects/{id}/chat` answers a student's question grounded
  in their uploaded material — see `app/services/rag/`. Each turn: `query_rewrite.py`
  condenses follow-ups against chat history and (config-permitting) expands the question
  into a HyDE hypothetical answer plus a few reworded variations; `retriever.py` embeds
  every variant, searches per-subject child-chunk embeddings, and fuses the ranked lists
  with Reciprocal Rank Fusion, resolving each hit's parent chunk for fuller context;
  `rerank.py` re-scores the fused candidates with one more LLM call (no local
  cross-encoder — stays cloud-only) before `chat_service.py` generates a citation-annotated
  answer (document/page/section) and persists both the user's and assistant's messages.
  Every technique (`rag_enable_hyde`, `rag_enable_multi_query`, `rag_enable_rerank`) is a
  `.env` flag, so a stricter free-tier model can have some switched off with no code change.
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
(the `pgvector/pgvector:pg16` Docker image already includes it — see `docker-compose.yml`).
Migration `0003` adds the `conversations`/`messages` tables for Phase 4's chat:

    python -m alembic upgrade head

## Run the API

    python -m uvicorn app.main:app --reload

Docs at `http://localhost:8000/docs`.

## Run the tests

    python -m pytest

121 tests. Almost none of them call a real LLM/embedding API or need Postgres running:
unit tests exercise services (`AuthService`, `SubjectService`, `DocumentService`,
`ConceptTagger`, `IngestionPipeline`, and Phase 4's `query_rewrite`/`retriever`/`rerank`/
`ChatService`) against in-memory fake repositories/providers; extractor tests run the real
PDF/DOCX/PPTX/XLSX parsers against small files generated on the fly (a real
`reportlab`-generated PDF, a real `python-docx` document, a real `python-pptx` deck with an
embedded image, etc. — not mocks), with the vision-model calls (scanned PDF pages, slide
images, standalone images) swapped for a fake that still exercises the real
image-rendering/extraction code path; integration tests hit the real FastAPI app end to
end against an in-memory SQLite database, including a full upload → extract → chunk →
embed → concept-tag run.

The one exception: `tests/integration/test_embedding_search_pgvector.py` and
`test_chat_api.py` run against a **real embedded Postgres+pgvector** (via the `pgserver`
pip package — no docker/root needed) instead of SQLite, because pgvector's cosine-distance
operator (`<=>`) genuinely doesn't exist on SQLite and mocking that query wouldn't prove
anything. See the `pg_server`/`pg_engine`/`pg_client` fixtures in `tests/conftest.py`.

If you already had `backend/.venv` from an earlier phase, re-run
`pip install -r requirements.txt` — this phase added `pgserver` (test-only).

## LLM configuration

All LLM and embedding calls are cloud APIs — nothing runs locally. See
`../docs/LLM_PROVIDERS.md` for the provider comparison and rationale. Defaults to Gemini
for both chat (concept tagging, and now RAG chat's condense/expand/rerank/answer calls) and
embeddings. Groq, OpenRouter, and OpenAI are implemented behind the same `LLMProvider`
interface (`app/services/llm/`) — switching is a `.env` change (`LLM_PROVIDER=groq`, etc.),
not a code change. RAG-specific tuning (`RAG_ENABLE_HYDE`, `RAG_ENABLE_MULTI_QUERY`,
`RAG_ENABLE_RERANK`, `RAG_RETRIEVAL_TOP_K`, `RAG_FINAL_CONTEXT_CHUNKS`, etc.) lives in
`app/core/config.py` and is also `.env`-overridable, so a stricter free-tier quota can turn
off the extra LLM calls (HyDE, multi-query, rerank) without touching code.
