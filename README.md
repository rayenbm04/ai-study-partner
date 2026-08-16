# AI Study Coach (Prof IA personnel)

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%2Bpgvector-336791?logo=postgresql&logoColor=white)
![Expo](https://img.shields.io/badge/Expo-React%20Native%20%2B%20web-000020?logo=expo&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Gemini](https://img.shields.io/badge/LLM-Gemini%20(default)-8E75B2?logo=googlegemini&logoColor=white)
![Cerebras](https://img.shields.io/badge/LLM-Cerebras-F05A28)
![Groq](https://img.shields.io/badge/LLM-Groq%20fallback-F55036)

Turns a student's own course material — lecture PDFs, handouts, past exams, corrected exercises — into a personal AI tutor that explains the course, helps memorize it, identifies what the student doesn't actually understand, trains them with practice, and measures their progress over time.

The differentiator over a generic "ChatGPT for students" is a **persistent pedagogical memory**: the app tracks what a student has learned, what they're forgetting, and what to work on next, instead of starting from zero in every conversation. Every AI call runs on a cloud LLM behind one swappable interface — Gemini by default, with Groq, Cerebras, OpenRouter, OpenAI, or Anthropic available with a `.env` change, no code change. See [Multi-provider LLM strategy](#multi-provider-llm-strategy-cerebras--groq) below for why two free cloud providers beat betting on one.

---

## How it works, in one picture

Uploaded course material is turned into a personal, per-subject knowledge base — not just handed to a generic LLM:

```
PDF / DOCX / PPTX / XLS / images
      │
      ▼
┌─────────────────────────┐
│  Text extraction         │  vision-model fallback for scanned pages/images
└────────────┬─────────────┘
             ▼
┌─────────────────────────┐
│  Hierarchical chunking   │  parent chunks (context) + child chunks (retrieval)
└────────────┬─────────────┘
             ▼
┌─────────────────────────┐
│  Embeddings               │  stored in pgvector
└────────────┬─────────────┘
             ▼
┌─────────────────────────┐
│  Concept tagging          │  LLM tags each chunk against the subject's concept graph
└────────────┬─────────────┘
             ▼
   Student asks a question / requests a summary, flashcards, or a quiz
             │
             ▼
┌─────────────────────────┐
│  Retrieval + citations    │  answer grounded in *the student's own material*
└────────────┬─────────────┘  (document, page, section) — never general knowledge
             ▼
   Chat • Summaries • Flashcards • Quizzes/Exams • Progress • Study Plan
```

Every student-facing feature reads from and writes back to that same per-subject concept graph, which is what makes this a tutor with memory rather than a chat log. Full step-by-step breakdown of both the ingestion side and the retrieval/answer side above, accurate to the current code: [`docs/RAG_PIPELINE.md`](docs/RAG_PIPELINE.md).

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│              Mobile / Web (Expo — React Native + web)              │
│  Auth │ Subjects │ Chat │ Materials │ Flashcards │ Quiz │ Progress │
│  Study Plan │ Settings                                             │
└──────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS (Bearer JWT)
┌──────────────────────────────▼──────────────────────────────────────┐
│                        FastAPI Backend                              │
│      api/v1 (routes)  →  services (one package per engine)  →       │
│      domain (framework-free entities/ports)  →  repositories  →     │
│      infrastructure (db, storage, vector store)                     │
│                                                                       │
│  Auth + Subjects · Schools · Curriculum + Subject Packs · Account    │
│  Knowledge Base (ingest/chunk/embed/tag) · RAG Chat · Summaries      │
│  Flashcards (SM-2) · Quiz + Exam engine · Progress engine            │
│  Planning engine · Analytics engine · Usage tracking                 │
└───────────┬───────────────────────────────────┬─────────────────────┘
            │                                   │
┌───────────▼───────────────┐     ┌─────────────▼─────────────────────┐
│   PostgreSQL + pgvector    │     │           AI Gateway               │
│   users · subjects · docs  │     │   services/llm/, services/embed/   │
│   chunks · embeddings      │     │   one interface, swappable via     │
│   concepts · flashcards    │     │   .env — see below                 │
│   quizzes · progress ·     │     └─────────────────────────────────────┘
│   study plans · usage      │
└─────────────────────────────┘
```

- **Backend:** FastAPI (Python), clean/layered architecture (API → services → domain → repositories → infrastructure) — see [`backend/README.md`](backend/README.md) for the full technical breakdown.
- **RAG (Retrieval-Augmented Generation):** the extraction → chunking → embedding → vector-search pipeline above is what lets the AI answer *from the course* instead of from general training knowledge.
- **Storage:** PostgreSQL for everything — users, subjects, chat history, flashcards, progress — with the `pgvector` extension holding embeddings in the same database, rather than a separate vector store to operate.
- **Frontend:** a native-first Expo (React Native + web) app in `mobile/` — one codebase targets iOS, Android, and web. This replaced the original plan to evolve the forked `rag-frontend` React/Vite app into the new frontend; `rag-frontend` is left untouched and unused going forward. See [`mobile/README.md`](mobile/README.md) for what's built.

The full system design — the six-engine model (Knowledge Base, Student Memory, Assessment, Learning/Progress, Planning, Analytics), database schema, API contract, and rollout plan — is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The cloud LLM/embedding provider comparison and free-tier strategy is in [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md).

---

## Multi-provider LLM strategy (Cerebras + Groq)

Every "free" cloud LLM tier has a ceiling — the fix isn't finding one magical provider with no limits, it's combining two so a ceiling on one doesn't stall the app. **Cerebras** is the interesting one to add: its free tier currently gives **GPT-OSS-120B** 30 requests/minute, 14.4K requests/day, and 1M tokens/day, with similarly generous limits on its 8B model — no credit card required, and generous enough that Groq becomes the fallback instead of the primary.

```
┌───────────────────────────┐
│           User            │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│      FastAPI Backend      │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  Check user's daily quota │  UsageService — per-user request budget,
│                           │  independent of whichever provider serves the call
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  RAG Retrieval             │  hybrid search → rerank
│                           │  (see "How it works, in one picture" above)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  AI Gateway               │  services/llm/factory.py — routes by task,
│                           │  retries the fallback on a 429 or missing capability
└───────────────────────────┘
   ├── Cerebras  (primary — gpt-oss-120b / llama3.1-8b aux)
   └── Groq      (fallback — on 429, exhausted daily quota, or a vision call)
```

**Task routing**, once `LLM_PROVIDER=cerebras` + `LLM_FALLBACK_PROVIDER=groq` are set:

| Task | Model |
|---|---|
| Tutoring / chat answers (reasoning-heavy) | Cerebras `gpt-oss-120b` |
| Concept tagging, classification, summaries, flashcard/quiz generation, RAG query rewriting | Cerebras `llama3.1-8b` — the same main/simple split every provider uses (`services/llm/factory.py`) |
| Any vision call (scanned PDF pages, standalone images) | Routed straight to Groq — Cerebras has no vision-capable model at all |
| Whenever Cerebras returns a 429 or its daily quota is exhausted | Groq (`openai/gpt-oss-120b` for answers, `openai/gpt-oss-20b` for aux) |

Implemented as `FallbackLLMProvider` (`backend/app/services/llm/fallback_provider.py`), built by `build_llm_provider`/`build_simple_llm_provider` whenever `LLM_FALLBACK_PROVIDER` differs from `LLM_PROVIDER` — unset (the default) means no wrapping at all, same single-provider behavior as before this existed. The per-user quota check happens in the backend's own code (`UsageService`), ahead of both RAG retrieval and the AI Gateway — it's a budget on *your* users, separate from (and enforced before you ever hit) whatever rate limit either provider imposes on you.

> Exact Cerebras model IDs and limits move — check [inference.cerebras.ai/docs](https://inference.cerebras.ai/docs) before relying on `CEREBRAS_CHAT_MODEL` / `CEREBRAS_SIMPLE_CHAT_MODEL`'s defaults for capacity planning.

Full provider comparison, rate limits, and the card-free local-embedding fallback are in [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md).

---

## Features

### 1. Understand the course (chat)

> "Explain Newton's first law like I'm 12."

Answered strictly from the material the student actually uploaded, with citations back to the source document, page, and section — not a generic textbook answer.

### 2. Memorize efficiently

The course is automatically turned into:

- **flashcards** (question/answer pairs, calibrated difficulty, linked back to concepts),
- **summaries** (short, detailed, bullet-point, key-concepts glossary, formula sheet, term definitions),

reviewed on a **spaced-repetition** schedule (the SM-2 algorithm) that spaces reviews out further each time a card is recalled successfully — day 1, day 3, day 7, day 15, and so on — so a student reviews right before they'd otherwise forget, not on a fixed calendar.

### 3. Get their gaps identified

Every concept gets a 0-100 mastery score computed from flashcard review grades and quiz/exam answer correctness, rolled up from individual concepts to chapters to the whole subject. Repeated wrong answers, noticeably slow answers, or a score that's dropped since it was last measured each flag a concept as a "weak concept" — a concrete, ranked list of what to focus on next, not just a vague sense of struggling.

> "You've mastered 85% of the Electricity chapter, but you're struggling with series-circuit laws."

### 4. Get tested

The course is turned into quizzes (mcq, true/false, short answer, calculation, fill-in-the-blank) and exams (a quiz with a duration and a style tag, e.g. "past-exam"), auto-graded — objective question types by exact match, open-ended ones by an LLM judging substantive equivalence — with the correct answer and explanation for each question revealed only after the attempt is submitted.

> "Generate a quiz on this chapter." / "Generate a one-hour exam."

### 5. Get an exam-prep plan

Given a deadline ("exam in 30 days") and how much time is available per day, the app builds a day-by-day plan across one or more subjects — weak and never-touched concepts scheduled first, a full-subject review session reserved for the day before the exam.

> "Generate a study plan for Physics and Chemistry, 45 minutes a day, exam on the 20th."

### 6. See it all in one place

A per-subject and cross-subject analytics view — documents, flashcards (and how many are due), quiz/exam counts and average scores, conversations, average mastery, and weak-concept counts — computed on the fly from what the other five engines already track, with no separate tracking layer of its own.

### Ingestion efficiency

- **Upload dedup**: a byte-identical re-upload to the same subject (sha256 of the raw content) returns the existing document instead of reprocessing it — no extra embedding/LLM spend on accidental duplicate uploads.
- **Granular progress**: while a document is `processing`, the API also reports `extracting → chunking → embedding → classifying` and a progress percentage, instead of a single opaque spinner state.
- **Two-phase ingestion**: a document is committed `ready` (and usable for RAG chat) as soon as extraction/chunking/embedding/classification are done; concept tagging — the knowledge-graph enrichment behind progress/planning — runs afterward as a best-effort follow-up, so a tagging failure never un-readies an already-indexed document.

### Usage tracking

Every document upload and AI request is logged per user (`UsageService`) — architecture for a future free/premium tier, not a paywall today, since the backend currently runs on one shared provider API key. Limit *enforcement* is a config flag away from live (`USAGE_LIMITS_ENABLED`, off by default) — flip it on once tiers actually exist, no code change needed.

## Inputs

- **Course material:** lecture PDFs, handouts, summary sheets, digital textbooks.
- **Assessment material:** past exams, corrected exercises, grading rubrics, supervised assignments.

Everything is scoped per subject, so a student's knowledge base for Physics stays entirely separate from Math or History.

---

## Status: vision vs. what's built

| Vision feature | Status |
|---|---|
| Import course material (PDF/DOCX/PPTX/XLS/images) | ✅ Built — Knowledge Base engine |
| Chat with the course, with citations | ✅ Built — RAG chat |
| Auto-generated summaries (6 types) | ✅ Built — Summary engine |
| Auto-generated flashcards + spaced repetition | ✅ Built — Flashcard engine (SM-2) |
| Quiz / exam generation + grading | ✅ Built — Quiz + Exam engine |
| Progress / mastery rollup | ✅ Built — Progress engine |
| Gap detection ("weak concepts") | ✅ Built — Progress engine |
| Exam-prep study plan | ✅ Built — Planning engine |
| Analytics dashboard | ✅ Built — Analytics engine, surfaced in the mobile app's home/progress screens |
| Per-user usage tracking (free/premium groundwork) | ✅ Built — logged today, enforcement off by default |
| School/teacher dashboard | ⏳ Not started |

In other words: every engine in the six-engine design is now built and working end to end — "explain, memorize, test, detect gaps, plan revision, see the analytics" all have a working API, and the mobile app (see Project layout below) covers most of them through a UI, with a short list of remaining gaps tracked in `mobile/README.md`.

---

## Project layout

```
ai-study-partner/
├── backend/            FastAPI backend — active development, see backend/README.md
├── mobile/             Expo (React Native + web) client — active development
├── rag-backend/        original forked project this was redesigned from,
├── rag-frontend/       left running untouched during the transition
└── docs/
    ├── ARCHITECTURE.md     six-engine architecture, database schema, API contract
    └── LLM_PROVIDERS.md    cloud LLM/embedding provider comparison + free-tier strategy
```

---

## Getting started

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in at least one LLM provider API key — see below
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0
```

Postgres with the `pgvector` extension is required (see `backend/docker-compose.yml` for a local one). Interactive API docs at `http://127.0.0.1:8000/docs`. Full setup, migrations, testing, and the complete endpoint reference are in [`backend/README.md`](backend/README.md).

### Mobile / web client

```bash
cd mobile
npm install
cp .env.example .env       # point EXPO_PUBLIC_API_URL at your running backend
npx expo start
```

Press `w` for web, `i` for iOS simulator, `a` for Android emulator, or scan the QR code with Expo Go. Design system, structure, and what's built vs. pending are in [`mobile/README.md`](mobile/README.md).

### Minimal LLM configuration

See [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md) for the full comparison; the short version:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `gemini` (default) \| `groq` \| `cerebras` \| `openrouter` \| `openai` |
| `LLM_FALLBACK_PROVIDER` | second provider to retry against on a rate limit or missing vision support — see [Multi-provider LLM strategy](#multi-provider-llm-strategy-cerebras--groq) above |
| `EMBEDDING_PROVIDER` | `gemini` (default) \| `local` — card-free CPU `sentence-transformers`, no key/network call after first use |

No card required to run this stack end to end: `LLM_PROVIDER=groq` or `LLM_PROVIDER=cerebras` need no billing account, and `EMBEDDING_PROVIDER=local` needs no cloud call at all.

---

## Technical decisions

**Why Cerebras + Groq instead of one provider?**
Every free cloud LLM tier has a ceiling — the fix isn't finding a provider with no limits (there isn't one), it's combining two so neither one's ceiling stalls the app. Cerebras' free tier (GPT-OSS-120B at 30 req/min, 14.4K req/day, 1M tokens/day) is generous enough to be the primary, with Groq — already integrated for the main/simple model split every provider uses — as a natural fallback the moment Cerebras returns a 429 or its daily quota resets past zero.

**Why check the user's quota before the AI Gateway, not after?**
Provider rate limits protect the provider's infrastructure, not this app's own cost/abuse exposure — a single user could still exhaust the shared Groq/Cerebras/Gemini quota for everyone else. A per-user daily request check in the backend's own code, ahead of retrieval and ahead of the AI Gateway, is a cheap guardrail that's independent of whichever provider ends up serving the call.

**Why pgvector instead of a separate vector database?**
Almost everything in this app is relational and needs transactions and joins with the vector data (e.g. "which chunks support this weak concept"). Running two databases in sync is unnecessary complexity at this stage; pgvector is fast enough at this scale and keeps one source of truth.

**Why a native Expo app instead of evolving the forked React/Vite frontend?**
The product is used mainly on mobile. One Expo codebase (React Native + web) targets iOS, Android, and web from day one, instead of building a mobile app on top of a web-first component library later. `rag-frontend` is left untouched and unused going forward.

**Why cloud LLMs only, no local inference?**
Cloud APIs' free tiers (Gemini, Groq, Cerebras, OpenRouter) are generous enough for this scale of usage and remove the GPU/VRAM requirement entirely — a student's phone or a low-spec laptop can run the client while all inference happens server-side. See [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md) for the full reasoning and the card-free path if a provider's free tier ever requires a billing account on file.

---

## Further reading

- [`backend/README.md`](backend/README.md) — full technical breakdown: layered architecture, every engine, migrations, LLM configuration, complete API reference, testing.
- [`mobile/README.md`](mobile/README.md) — design system, i18n, structure, API client, what's built vs. pending.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the six-engine model, database schema, API contract, rollout plan (pre-implementation design doc).
- [`docs/RAG_PIPELINE.md`](docs/RAG_PIPELINE.md) — as-built, step-by-step walkthrough of ingestion (extract → chunk → embed → classify → tag) and retrieval (condense → expand → retrieve → rerank → answer), accurate to the current code.
- [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md) — cloud LLM/embedding provider comparison, the Cerebras + Groq strategy in full, and the card-free local-embedding fallback.
