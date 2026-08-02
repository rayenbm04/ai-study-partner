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

Everything the student-facing features do — chat, summaries, flashcards, quizzes/exams, and eventually progress tracking — reads from and writes back to that same per-subject concept graph, which is what makes the system a tutor with memory rather than a chat log.

## What a student can do with it

### 1. Understand the course (chat)

> "Explain Newton's first law like I'm 12."

Answered strictly from the material the student actually uploaded, with citations back to the source document, page, and section — not a generic textbook answer.

### 2. Memorize efficiently

The course is automatically turned into:

- **flashcards** (question/answer pairs, calibrated difficulty, linked back to concepts),
- **summaries** (short, detailed, bullet-point, key-concepts glossary, formula sheet, term definitions),

reviewed on a **spaced-repetition** schedule (the SM-2 algorithm) that spaces reviews out further each time a card is recalled successfully — day 1, day 3, day 7, day 15, and so on — so a student reviews right before they'd otherwise forget, not on a fixed calendar.

### 3. Get their gaps identified *(planned)*

By analyzing answers, repeated mistakes, response time, and which chapters keep coming up wrong:

> "You've mastered 85% of the Electricity chapter, but you're struggling with series-circuit laws. Here's a focused 20-minute session."

### 4. Get tested

The course is turned into quizzes (mcq, true/false, short answer, calculation, fill-in-the-blank) and exams (a quiz with a duration and a style tag, e.g. "past-exam"), auto-graded — objective question types by exact match, open-ended ones by an LLM judging substantive equivalence — with the correct answer and explanation for each question revealed only after the attempt is submitted.

> "Generate a quiz on this chapter." / "Generate a one-hour exam."

### 5. Get an exam-prep plan *(planned)*

Given a deadline ("exam in 30 days"), the app builds a day-by-day plan from the student's current mastery, available study time, and priority weak spots.

## Inputs

- **Course material:** lecture PDFs, handouts, summary sheets, digital textbooks.
- **Assessment material:** past exams, corrected exercises, grading rubrics, supervised assignments.

Everything is scoped per subject, so a student's knowledge base for Physics stays entirely separate from Math or History.

## Architecture

- **Backend:** FastAPI (Python), clean/layered architecture (API → services → domain → repositories → infrastructure) — see [`backend/README.md`](backend/README.md) for the full technical breakdown.
- **AI:** cloud LLMs only — Gemini by default, swappable to Groq, OpenRouter, OpenAI, or Anthropic behind one interface with a config change, no code change. Nothing runs locally; no on-disk model weights anywhere in the pipeline.
- **RAG (Retrieval-Augmented Generation):** the extraction → chunking → embedding → vector-search pipeline described above is what lets the AI answer *from the course* instead of from general training knowledge.
- **Storage:** PostgreSQL for everything — users, subjects, chat history, flashcards, progress — with the `pgvector` extension holding embeddings in the same database, rather than a separate vector store to operate.
- **Frontend:** not yet migrated off the original forked React app; a page-by-page TypeScript rewrite is planned as each page is touched, rather than a big-bang rewrite.

The full system design — the six-engine model (Knowledge Base, Student Memory, Assessment, Learning/Progress, Planning, Analytics), database schema, API contract, and rollout plan — is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The cloud LLM/embedding provider comparison and free-tier strategy is in [`docs/LLM_PROVIDERS.md`](docs/LLM_PROVIDERS.md).

## Status: vision vs. what's built

| Vision feature | Status |
|---|---|
| Import course material (PDF/DOCX/PPTX/XLS/images) | ✅ Built — Knowledge Base engine |
| Chat with the course, with citations | ✅ Built — RAG chat |
| Auto-generated summaries (6 types) | ✅ Built — Summary engine |
| Auto-generated flashcards + spaced repetition | ✅ Built — Flashcard engine (SM-2) |
| Quiz / exam generation + grading | ✅ Built — Quiz + Exam engine |
| Progress / history | 🚧 Partial — chat, review, and quiz/exam attempt history exist; mastery scoring doesn't yet |
| Gap detection ("weak concepts") | ⏳ Planned — Progress engine |
| Exam-prep study plan | ⏳ Planned — Planning engine |
| Analytics dashboard | ⏳ Planned — Analytics engine |
| School/teacher dashboard | ⏳ Not started |

In other words: "explain, memorize, test" is built and working end to end; "detect gaps, plan revision" is designed (see the rollout plan in `docs/ARCHITECTURE.md`) but not yet implemented.

## Project layout

- `backend/` — the FastAPI backend described above; active development, see its README for setup and testing.
- `rag-backend/`, `rag-frontend/` — the original forked project this was redesigned from, left running untouched during the transition (the new `backend/` never modifies them).
- `docs/ARCHITECTURE.md` — full six-engine architecture, database schema, API contract, rollout plan.
- `docs/LLM_PROVIDERS.md` — cloud LLM/embedding provider comparison and free-tier-first strategy.

## Getting started

See [`backend/README.md`](backend/README.md) for setup, running the database migrations, starting the API, and running the test suite.
