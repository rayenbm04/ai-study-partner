# RAG Pipeline — As Built

An accurate, implementation-level walkthrough of how a document becomes searchable and how a chat question gets answered — as opposed to [`ARCHITECTURE.md`](ARCHITECTURE.md), which is the pre-implementation design doc. This is what the code in `backend/app/services/knowledge_base/` and `backend/app/services/rag/` actually does today; if the two ever disagree, this file and the code should be treated as the source of truth, `ARCHITECTURE.md` as historical intent.

The pipeline splits into two independent phases: **ingestion** (building the knowledge base once, per document) and **retrieval** (answering a question from it, every chat turn).

---

## 1. Ingestion — turning a document into searchable, tagged chunks

Runs as a background task (`app/services/knowledge_base/ingestion_task.py`) scheduled right after upload, so the upload HTTP response returns fast regardless of file size — the caller polls `GET /documents/{id}` for status.

### Dedup check, before any processing starts

`DocumentService.upload` (`app/services/document_service.py`) hashes the raw uploaded bytes (sha256, `documents.content_hash`). A byte-identical file already uploaded to the same subject returns the existing document instead of being reprocessed — no wasted embedding/LLM spend on an accidental duplicate upload. Toggle: `DOCUMENT_DEDUP_ENABLED` (default `true`).

### `IngestionPipeline.run()` — extract → chunk → embed → classify → ready

Updates `documents.processing_step` / `processing_progress` at each stage, surfaced through `GET /documents/{id}` for a granular upload UI:

```
extracting (10%) → chunking (35%) → embedding (55%) → classifying (85%) → ready
```

1. **Extract** — format-specific extractors (`app/services/knowledge_base/extractors/`) pull text segments: `pdfplumber` for PDF, `python-docx` for DOCX, `python-pptx` for PPTX, `openpyxl`/`xlrd` for XLS(X). Scanned or image-only pages fall back to the configured vision model (`LLMProvider.complete_vision`) for transcription. Extraction runs on the *main* model tier — transcription quality matters and these calls are already infrequent by design.
2. **Chunk** (`app/services/knowledge_base/chunking.py`) — character-based, no tokenizer dependency. Each extracted segment is split into a **parent chunk** (`CHUNK_PARENT_CHARS`, default 900 chars) — enough surrounding context for coherent concept tagging and citations — which is further split into **child chunks** (`CHUNK_CHILD_CHARS`, default 220 chars, `CHUNK_OVERLAP_CHARS` = 40-char overlap between consecutive children) — the small units that actually get embedded and searched. Splitting respects natural text boundaries in order (`\n\n` → `\n` → `. ` → ` `) before falling back to a hard character cut, so a chunk boundary rarely lands mid-sentence.
3. **Embed** — only child chunks are embedded (parent chunks exist purely for context assembly, never searched directly), batched through the configured `EmbeddingProvider` (`EMBEDDING_BATCH_SIZE` texts per call, up to `EMBEDDING_MAX_CONCURRENCY` batches concurrently) and stored in `pgvector`.
4. **Classify** — one LLM call (*simple* model tier) over the joined parent-chunk text (capped at `CLASSIFICATION_MAX_SOURCE_CHARS`) determines `document_type` and, above `CLASSIFICATION_CONFIDENCE_THRESHOLD`, places the document in the curriculum chapter/lesson tree.
5. **No extractable text → fail fast.** If chunking produces zero parent chunks (a scanned PDF whose vision fallback also failed, or a genuinely empty file), the pipeline raises rather than silently reaching `ready` with no content — the document is marked `failed` with an honest status instead of getting stuck "ready" with nothing to answer from.
6. **Mark ready** — page count recorded; the document is now usable for RAG chat.

### Concept tagging — a separate, best-effort follow-up

`IngestionPipeline.tag_concepts()` runs *after* `ready` is committed, in its own transaction: parent chunks are batched (`CONCEPT_TAG_BATCH_SIZE`, default 6 per LLM call, *simple* model tier) and tagged against the subject's concept graph (`concept_tag_relevance_threshold`, `max_new_concepts_per_chunk`). This is deliberately decoupled from `run()` — concept tagging is the highest-volume LLM step in ingestion (one batch call per handful of chunks) and powers progress/planning, not chat; a tagging failure is logged and never un-readies a document whose RAG index is already complete.

---

## 2. Retrieval + answer — one chat turn

`ChatService.send_message()` (`app/services/rag/chat_service.py`) orchestrates this, per message:

1. **Condense the question** (`query_rewrite.condense_question`) — if there's conversation history (last `RAG_HISTORY_MESSAGES` turns, default 6), one LLM call rewrites a follow-up ("what about the second one?") into a standalone question, resolving pronouns/implicit references using that history. No-op if there's no history yet, or if the call fails (falls back to the raw question).
2. **Expand the query** (`query_rewrite.expand_query`) — one combined structured-JSON LLM call produces:
   - **HyDE** (`RAG_ENABLE_HYDE`) — a hypothetical answer to the question. Embedding a plausible *answer* tends to land closer to real supporting passages in vector space than embedding the *question* does.
   - **Multi-query** (`RAG_ENABLE_MULTI_QUERY`, `RAG_MULTI_QUERY_COUNT` variations, default 3) — reworded versions of the same question, each using different terminology/specificity, to catch passages the original phrasing might miss.
   
   Both flags are independent — either or both can be switched off for a slower or stricter free-tier model. A failed expansion call falls back to no expansion (just the condensed question).
3. **Retrieve per variant** (`retriever.VectorRetriever.retrieve`) — every query string (condensed question + HyDE answer + variations) is embedded and vector-searched independently against `pgvector` (`RAG_RETRIEVAL_TOP_K` results per variant), optionally narrowed to a single `document_id` for "ask about this upload" style questions. The per-query ranked lists are merged with **Reciprocal Rank Fusion** (`_RRF_K = 60`, the standard damping constant) — a chunk that ranks well across *multiple* variants scores higher than one that only shows up in one, without needing to normalize raw embedding-distance scores across differently-worded queries (which aren't comparable in a principled way to begin with).
4. **Assemble context** — retrieval matches on child chunks (small, embedding-precise), but the text actually handed downstream is the corresponding *parent* chunk's content where available (`RetrievedChunk.context_text`) — enough surrounding context to answer from without diluting what got embedded. Citations still reference the child chunk's own page/section, since that's the more precise location. A pool of `2 × RAG_FINAL_CONTEXT_CHUNKS` candidates is kept at this point (when reranking is on) so the next step has something meaningful to choose between.
5. **Rerank** (`rerank.rerank`, `RAG_ENABLE_RERANK`) — RRF fusion is only a distance-based proxy; it has no idea whether a chunk that happens to be nearby in vector space actually *answers* the question. One structured-JSON LLM call (*simple* model tier, temperature 0) scores every candidate's relevance (0–1) to the question; results are re-sorted by that score and truncated to `RAG_FINAL_CONTEXT_CHUNKS` (default 6). Falls back silently to the RRF order, truncated the same way, if the call fails or returns something unparseable — reranking is a quality improvement, not a hard dependency.
6. **Generate the answer** — the final candidates are numbered into excerpts and sent to the *main* model with a system prompt that forces citation-grounded answering: *"Answer the student's question using ONLY the numbered excerpts below... if the excerpts don't contain the answer, say so plainly rather than guessing from general knowledge... Reference excerpts inline using their number in square brackets, e.g. [1]."* If retrieval returned nothing at all, no LLM call is made — the student gets a direct "I couldn't find anything in your uploaded material for this subject that addresses that question" instead.
7. **Persist and log** — both the user's message and the assistant's reply (with structured `Citation`s: document, filename, chunk, page, section) are saved; a `usage_events` row (`event_type="chat_message"`) is recorded per the Usage tracking engine (see `backend/README.md`).

Every retrieval-support call — condense, expand, rerank — runs on the *simple*/cheap model tier (`build_simple_llm_provider`); only the final answer generation uses the *main* model. This mirrors the same main/simple split used during ingestion (extraction on main, classification/tagging on simple) — see [`LLM_PROVIDERS.md`](LLM_PROVIDERS.md) for the full provider strategy, including the Cerebras + Groq fallback.

---

## Why the parent/child split exists

Embeddings work best over small, focused, single-topic-ish spans — that's what child chunks are for. But an LLM answering a question needs more surrounding context than a 220-character fragment gives it, or the answer reads as disjointed and citation-poor. Splitting the two roles — child chunks for the embedding/search target, parent chunks for what the LLM actually reads — gets both properties instead of trading one off against the other. The same split is why concept tagging (which needs coherent, standalone text) runs against parent chunks while retrieval matches on child chunks.

## Testability

Every stage here — `chunking.py`, `query_rewrite.py`, `retriever.py`, `rerank.py`, `IngestionPipeline`, `ChatService` — is unit-tested independently against fakes (fake repositories, a fake `LLMProvider`, a fake `EmbeddingProvider`), with no network call and no database. See `backend/tests/unit/test_chunking.py`, `test_query_rewrite.py`, `test_retriever.py`, `test_rerank.py`, `test_ingestion_pipeline.py`, and `test_chat_service.py`. A small number of integration tests (`test_chat_api.py`, `test_embedding_search_pgvector.py`) run the same pipeline against a real embedded Postgres+pgvector instance to cover what fakes can't — actual cosine-distance search behavior.
