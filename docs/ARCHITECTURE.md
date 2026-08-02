# AI Study Coach — Phase 1 Architecture

Redesign of the forked `rag-assistant` project into a multi-subject, six-engine learning platform. This document covers architecture, folder structure, database schema, API contract, and rollout plan. No implementation yet — this is the design to review before Phase 2 (Auth + Subjects) starts.

## 1. What the fork already gives us

The current `rag-backend` is a single 3,200-line `main.py`: FastAPI + SQLite (users only) + ChromaDB + LlamaIndex, one global document index, no subject boundary, no student model. It's a solid RAG prototype, not a platform. Rather than rewrite from zero, the pieces below get extracted and reused; everything else is replaced.

**Reuse as-is (port into new service modules, logic unchanged):**

- Document extractors — `extract_pdf_content`, `extract_docx_content`, `extract_pptx_content`, `extract_excel_content`, `extract_uml_content`, and the vision-model image analysis path (`analyze_image_with_llava`, cloud fallback via GPT-4o/Gemini). These are format-specific and already handle real student material (slides, scanned pages, UML). → `services/knowledge_base/extractors/`.
- RAG technique stack — HyDE expansion, multi-query expansion, query condensation from history, per-file retrieval, BM25 + vector fusion, cross-encoder reranking. This is genuinely above-average RAG work and stays. → `services/rag/`.
- Hierarchical parent-child chunking (`HierarchicalNodeParser`, leaf/parent split) — keeps chunk context without bloating embeddings. → `services/knowledge_base/chunking.py`.
- LLM provider abstraction (`_CompatLLM`, `_get_llm`, friendly error mapping) — the shape is right; extend it to a clean `LLMProvider` interface (`services/llm/`) covering OpenAI, Claude, Gemini, OpenRouter, and optionally Ollama for a free local tier.
- JWT auth pattern (bcrypt + jose) — reused, extended with refresh tokens.
- The eval harness (`eval.py`, `answer_eval.py`) — kept as an internal RAG-quality regression tool, pointed at the new schema.
- Frontend primitives — shadcn/ui setup, `Markdown.jsx` renderer, `Composer.jsx`, `UploadZone.jsx` — reused as components inside new pages, not thrown away.

**Replace:**

- ChromaDB + flat `node_store/docstore.json` → **PostgreSQL + pgvector**. Everything else in the app (users, subjects, progress, quizzes) is relational and needs transactions and joins with the vector data (e.g. "which chunks support this weak concept"). Running two databases in sync is unnecessary complexity at this stage; pgvector is fast enough for a single-institution or B2C scale and keeps one source of truth. Qdrant stays an option if retrieval volume later demands a dedicated vector engine — the repository layer is built behind an interface so that swap doesn't touch services.
- SQLite `rag_users.db` → same Postgres instance.
- Single-file `main.py` → layered app (routes / services / repositories / domain), so quiz logic, progress logic, and planning logic aren't all competing for space in one file.
- Global, subject-less index → every document, chunk, concept, flashcard, quiz, and progress row is scoped by `subject_id`.
- React JS (`.jsx`) → migrate to TypeScript incrementally, page by page, starting with new pages (Subjects, Progress, Study Plan) written in `.tsx` from day one; existing chat page converted when it's touched for the RAG phase. A big-bang rewrite isn't worth the risk right now.

## 2. The six-engine model

This is the actual product decision from the earlier discussion: the differentiator isn't the chatbot, it's the persistent student model. Concretely, that means a **Concept Graph** per subject (not just "chapters," but individual concepts with prerequisite edges) and a **mastery score** computed per concept, rolled up to chapter and subject level. Everything else — flashcards, quizzes, weak-concept detection, study plans — reads and writes against that graph instead of being independent features bolted onto a chat app.

| Engine | Responsibility | Core tables |
|---|---|---|
| Knowledge Base | Ingest documents, chunk, embed, tag chunks to concepts | `subjects`, `documents`, `chunks`, `embeddings`, `concepts`, `concept_prerequisites`, `concept_chunks` |
| Student Memory | Chat history + spaced-repetition state | `conversations`, `messages`, `flashcards`, `flashcard_reviews` |
| Assessment Engine | Quiz/exam generation and grading | `quizzes`, `quiz_questions`, `quiz_attempts`, `student_answers` |
| Learning Engine (Progress) | Mastery scoring, weak-concept detection | `progress`, `weak_concepts` |
| Planning Engine | Study sessions and revision scheduling | `study_plans`, `study_plan_items`, `study_sessions`, `revision_schedule` |
| Analytics Engine | Read-side aggregation over the above | no new tables — materialized views / query layer |

## 3. Database schema

```
users
  id (pk), email (unique), hashed_password, firstname, lastname, role, refresh_token_hash, created_at

subjects
  id (pk), user_id (fk users), name, description, color, icon, created_at, archived_at

documents
  id (pk), subject_id (fk subjects), original_filename, storage_path, file_type,
  status (pending|processing|ready|failed), page_count, uploaded_at, metadata (jsonb)

chunks
  id (pk), document_id (fk documents), subject_id (fk subjects, denormalized for query speed),
  content, chunk_type (parent|child), parent_chunk_id (fk chunks, nullable),
  page, section_title, chapter, token_count, metadata (jsonb)

embeddings
  id (pk), chunk_id (fk chunks), model_name, vector (vector(dim), pgvector), created_at

concepts
  id (pk), subject_id (fk subjects), name, description, parent_concept_id (fk concepts, nullable)

concept_prerequisites
  concept_id (fk concepts), prerequisite_id (fk concepts)   -- graph edges, DAG per subject

concept_chunks
  concept_id (fk concepts), chunk_id (fk chunks), relevance (float)   -- LLM-tagged during ingestion

conversations
  id (pk), user_id (fk users), subject_id (fk subjects), title, created_at

messages
  id (pk), conversation_id (fk conversations), role (user|assistant), content,
  citations (jsonb — document/page/section refs), created_at

flashcards
  id (pk), subject_id (fk subjects), concept_id (fk concepts, nullable),
  question, answer, difficulty, tags (jsonb), source (generated|manual), created_at

flashcard_reviews
  id (pk), flashcard_id (fk flashcards), user_id (fk users),
  ease_factor, interval_days, repetitions, last_grade, last_reviewed_at, next_review_date
  -- SM-2 state, one row per (user, flashcard)

quizzes
  id (pk), subject_id (fk subjects), user_id (fk users), title, kind (quiz|exam),
  difficulty, topics (jsonb), duration_minutes (nullable, exams), style (nullable, e.g. "past-exam"), created_at

quiz_questions
  id (pk), quiz_id (fk quizzes), concept_id (fk concepts, nullable),
  type (mcq|true_false|short_answer|calculation|fill_blank),
  question, options (jsonb, nullable), correct_answer, explanation, points, difficulty

quiz_attempts
  id (pk), quiz_id (fk quizzes), user_id (fk users), started_at, completed_at, score

student_answers
  id (pk), quiz_attempt_id (fk quiz_attempts), quiz_question_id (fk quiz_questions),
  answer, is_correct, time_spent_seconds, submitted_at

progress
  id (pk), user_id (fk users), concept_id (fk concepts),
  mastery_score (0-100), trend (up|down|flat), last_updated
  -- chapter/subject mastery is computed on read by aggregating child concepts, not stored redundantly

weak_concepts
  id (pk), user_id (fk users), concept_id (fk concepts),
  reason (repeated_errors|slow_response|decay), confidence, status (active|resolved), detected_at

study_sessions
  id (pk), user_id (fk users), subject_id (fk subjects), concept_id (fk concepts, nullable),
  activity_type (reading|flashcards|quiz|exam), started_at, ended_at, duration_seconds

study_plans
  id (pk), user_id (fk users), name, exam_date (nullable), daily_minutes_available, status, created_at

study_plan_items
  id (pk), study_plan_id (fk study_plans), subject_id (fk subjects), concept_id (fk concepts, nullable),
  scheduled_date, activity_type, duration_minutes, status (pending|done|skipped)

revision_schedule
  id (pk), user_id (fk users), concept_id (fk concepts),
  next_review_date, interval_days, algorithm (sm2|manual)
  -- covers concept-level "revisit this chapter" reminders distinct from per-card SM-2 state
```

Notes on the design: `quizzes.kind` distinguishes quiz vs. exam instead of duplicating tables — exams are quizzes with a duration, a style tag, and typically full-course topic coverage, so `exam_history` is just `quiz_attempts` filtered by `kind = 'exam'` plus a rubric field on the quiz. Every table that represents student-owned content carries `user_id` or is reachable through `subject_id → user_id`, since subjects are user-created and not shared by default — cross-user sharing (e.g. a teacher assigning a subject to a class) is a v2 concern and the schema doesn't block it, it's just not built now.

## 4. Backend folder structure

```
backend/
  app/
    main.py                      # app factory, router registration, startup
    core/
      config.py                  # pydantic-settings, env vars
      security.py                # JWT issue/verify, password hashing
      logging.py
      exceptions.py               # domain exception -> HTTP mapping
    api/v1/
      deps.py                     # get_current_user, get_db, pagination
      routes/
        auth.py
        subjects.py
        documents.py
        chat.py
        summaries.py
        flashcards.py
        quizzes.py
        exams.py
        progress.py
        study_plan.py
        analytics.py
    domain/                       # framework-free models + interfaces (ports)
      subject.py  document.py  concept.py  chunk.py
      flashcard.py  quiz.py  progress.py  study_plan.py
    services/                     # business logic, one package per engine
      knowledge_base/
        extractors/                # pdf.py, docx.py, pptx.py, xlsx.py, image.py (ported from main.py)
        chunking.py
        concept_tagger.py          # LLM-assigns chunks to concepts during ingestion
        ingestion_pipeline.py
      rag/
        retriever.py               # BM25 + vector fusion, per-subject filter
        rerank.py
        query_rewrite.py           # HyDE, multi-query, condense
        chat_service.py
      summary_engine/
      flashcard_engine/
        sm2.py
        generator.py
      quiz_engine/
      exam_engine/
      progress_engine/
        mastery.py                  # rollup from concept -> chapter -> subject
        weakness_detector.py
      planning_engine/
        scheduler.py
      analytics_engine/
      llm/
        base.py  openai_provider.py  claude_provider.py  gemini_provider.py  openrouter_provider.py  factory.py
      embeddings/
        base.py  openai_embedder.py  bge_embedder.py  factory.py
    repositories/                 # SQLAlchemy implementations of domain ports
      subject_repo.py  document_repo.py  chunk_repo.py  concept_repo.py
      flashcard_repo.py  quiz_repo.py  progress_repo.py  study_plan_repo.py
    infrastructure/
      db/
        base.py  session.py
        models/                   # SQLAlchemy ORM models, split by engine, mirrors schema above
      vector_store/
        pgvector_store.py         # implements a VectorStore port -> swappable for Qdrant later
      storage/
        local_storage.py  s3_storage.py
    prompts/                      # plain templates, no logic — loaded by services, never inlined
      tutor.py  quiz.py  flashcard.py  summary.py  exam.py  revision.py
  alembic/
  tests/
    unit/  integration/
  Dockerfile
```

Routes stay thin — they parse the request, call a service, return a response schema. All decision logic (how mastery is computed, when a card is due, how a plan is built) lives in `services/`, testable without spinning up FastAPI.

## 5. API contract (surface only, schemas in Phase 2+)

```
POST   /auth/register            POST /auth/login          POST /auth/refresh        GET /auth/me

GET    /subjects                 POST /subjects             PATCH /subjects/{id}       DELETE /subjects/{id}

POST   /subjects/{id}/documents           GET /subjects/{id}/documents
GET    /documents/{id}                    DELETE /documents/{id}

POST   /subjects/{id}/chat                GET /subjects/{id}/conversations
GET    /conversations/{id}/messages

POST   /subjects/{id}/summaries           GET /documents/{id}/summary

GET    /subjects/{id}/flashcards          POST /subjects/{id}/flashcards/generate
POST   /flashcards/{id}/review             GET /flashcards/due

POST   /subjects/{id}/quizzes/generate     GET /quizzes/{id}
POST   /quizzes/{id}/attempts              POST /quiz-attempts/{id}/answers    POST /quiz-attempts/{id}/submit

POST   /subjects/{id}/exams/generate       GET /exams/{id}/history

GET    /subjects/{id}/progress             GET /subjects/{id}/weak-concepts

POST   /study-plans                        GET /study-plans/{id}               PATCH /study-plan-items/{id}

GET    /analytics/subjects/{id}            GET /analytics/overview
```

## 6. Rollout

1. Auth + Subjects — replaces the current single-user-table auth with refresh tokens; introduces `subjects` as the top-level container everything else scopes to.
2. Knowledge Base — document upload, extraction, chunking, concept tagging, pgvector storage, scoped per subject.
3. RAG chat — port the HyDE/multi-query/rerank pipeline onto the new store, with citations back to document/page/section.
4. Summaries — short/detailed/bullet, key concepts, formula sheets, definitions, generated from the same retrieval layer.
5. Flashcards — generation + SM-2 review loop.
6. Quiz + Exam engine — generation, attempts, grading, explanations.
7. Progress engine — mastery rollup from concept graph, weak-concept detection from repeated wrong answers.
8. Planning engine — study plan generation from exam date + available time + current mastery.
9. Analytics — dashboards over everything above.
10. Frontend — Subjects, Upload, Chat, Flashcards, Quiz, Progress, Study Plan, Settings pages, reusing existing UI primitives, migrating to TypeScript as pages are (re)written.

Steps 1–3 are mostly relocation of working code into the new structure; the concept graph, mastery scoring, and weak-concept detection in steps 2 and 7 are genuinely new and are where most of the design risk sits — worth prototyping the concept-tagging step early (step 2) since the rest of the differentiator depends on it being accurate.

Ready to start on Phase 2 (Auth + Subjects) when you are — that's the smallest slice that both migrates working code and introduces the new subject boundary everything else depends on.
