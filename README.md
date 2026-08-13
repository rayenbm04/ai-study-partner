# AI Study Coach (Prof IA personnel)

## Vision

Turn a student's own course material — lecture PDFs, handouts, past exams, corrected exercises — into a personal AI tutor that can:

- explain the course,
- help memorize it,
- identify what the student doesn't actually understand,
- train them with practice, and
- measure their progress over time.

The differentiator over a generic "ChatGPT for students" is a **persistent pedagogical memory**: the app tracks what a student has learned, what they're forgetting, and what to work on next, instead of starting from zero in every conversation.

## How it works, in one picture

Uploaded course material (PDF, DOCX, PPTX, ...) is turned into a personal, per-subject knowledge base — not just handed to a generic LLM:

    PDF / DOCX / PPTX / images
          → text extraction (+ vision fallback for scanned pages/images)
          → chunking (parent chunks for context, child chunks for retrieval)
          → embeddings, stored in a vector database
          → LLM tags each chunk against a per-subject concept graph
                                    ↓
    student asks a question / requests a summary or flashcards
                                    ↓
    retrieval finds the relevant material → LLM answers *grounded in and
    citing the student's own material* (document, page, section) —
    never just general knowledge floating free of what they were actually taught

Everything the student-facing features do — chat, summaries, flashcards, quizzes/exams, and progress tracking — reads from and writes back to that same per-subject concept graph, which is what makes the system a tutor with memory rather than a chat log.

## What a student can do with it

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

## Inputs

- **Course material:** lecture PDFs, handouts, summary sheets, digital textbooks.
- **Assessment material:** past exams, corrected exercises, grading rubrics, supervised assignments.

Everything is scoped per subject, so a student's knowledge base for Physics stays entirely separate from Math or History.

## Architecture

- **Backend:** FastAPI (Python), clean/layered architecture (API → services → domain → repositories → infrastructure) — see [`backend/README.md`](backend/README.md) for the full technical breakdown.
- **AI:** cloud LLMs by default — Gemini by default, swappable to Groq, OpenRouter, OpenAI, or Anthropic behind one interface with a config change, no code change. Each provider is also two model tiers (a main model for reasoning-heavy work, a cheaper/faster one for mechanical high-volume calls like concept tagging and classification), picked the same way. Embeddings default to the cloud too, with a card-free local fallback (`EMBEDDING_PROVIDER=local`, an open-source `sentence-transformers` model cached on the backend's own CPU — no key, no network call after first use) for anyone who can't or won't put a billing card on file with a provider — see `docs/LLM_PROVIDERS.md`.
- **RAG (Retrieval-Augmented Generation):** the extraction → chunking → embedding → vector-search pipeline described above is what lets the AI answer *from the course* instead of from general training knowledge.
- **Storage:** PostgreSQL for everything — users, subjects, chat history, flashcards, progress — with the `pgvector` extension holding embeddings in the same database, rather than a separate vector store to operate.
- **Frontend:** a native-first Expo (React Native + web) app in `mobile/` — one codebase targets iOS, Android, and web. This replaced the original plan to evolve the forked `rag-frontend` React/Vite app into the new frontend; `rag-frontend` is left untouched and unused going forward. See [`mobile/README.md`](mobile/README.md) for what's built.

The full system design — the six-engine model (Knowledge Base, Student Memory, Assessment, Learning/Progress, Planning, Analytics), database schema, API contract, and rollout plan — is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The cloud LLM/embedding provider comparison and free-tier strategy is in [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md).

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
| School/teacher dashboard | ⏳ Not started |

In other words: every engine in the six-engine design is now built and working end to end — "explain, memorize, test, detect gaps, plan revision, see the analytics" all have a working API, and the mobile app (see Project layout below) covers most of them through a UI, with a short list of remaining gaps tracked in `mobile/README.md`.

## Project layout

- `backend/` — the FastAPI backend described above; active development, see its README for setup and testing.
- `mobile/` — the Expo (React Native + web) client; active development, see its README for setup, design system, and what's built vs. pending.
- `rag-backend/`, `rag-frontend/` — the original forked project this was redesigned from, left running untouched during the transition (the new `backend/`/`mobile/` never modify them).
- `docs/ARCHITECTURE.md` — full six-engine architecture, database schema, API contract, rollout plan.
- `docs/LLM_PROVIDERS.md` — cloud LLM/embedding provider comparison and free-tier-first strategy.

## Getting started

See [`backend/README.md`](backend/README.md) for setup, running the database migrations, starting the API, and running the test suite, and [`mobile/README.md`](mobile/README.md) for running the client.
