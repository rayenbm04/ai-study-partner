"""Application settings, loaded from environment variables / .env.

LLM/chat is always a cloud API key + model name. Embeddings default to a
cloud API too (Gemini) but can fall back to a local sentence-transformers
model (EMBEDDING_PROVIDER=local) — some "free" cloud embedding tiers now
require a billing account on file even though the tier itself doesn't
charge, which the local option sidesteps entirely (no key, no card, no
network call after the model is cached).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # Postgres + pgvector. asyncpg driver, async engine end to end.
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_study_coach"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    allowed_origins: str = "http://localhost:5173"

    # Login-attempt limiting.
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15

    # Email verification / password reset. No real email provider is wired up
    # yet (EMAIL_SENDER=logging just logs the link) — see app/services/email/.
    email_sender: str = "logging"  # logging | (a real provider, later)
    email_verification_token_expire_hours: int = 24
    password_reset_token_expire_minutes: int = 60

    # LLM providers. See docs/LLM_PROVIDERS.md.
    llm_provider: str = "gemini"          # gemini | groq | openrouter | openai
    embedding_provider: str = "gemini"    # gemini | local — see docs/LLM_PROVIDERS.md

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    # Empty means "reuse gemini_chat_model for simple tasks too" — Gemini's
    # lite tier naming has churned (see the groq_vision_model comment below
    # for how fast these move), so no default is guessed here; set to
    # something like "gemini-2.5-flash-lite" once you've confirmed it's live.
    gemini_simple_chat_model: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    # gemini-embedding-001 supports Matryoshka truncation up to 3072 dims; 768 is
    # Google's recommended quality/storage balance. Must match the pgvector
    # column width in the embeddings table migration if changed.
    embedding_dimension: int = 768

    # Local embedding fallback (EMBEDDING_PROVIDER=local) — no key, no card.
    # all-mpnet-base-v2 outputs 768-dim vectors, matching embedding_dimension
    # above exactly, so no migration is needed when switching to it.
    local_embedding_model: str = "sentence-transformers/all-mpnet-base-v2"

    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    # llama-3.3-70b-versatile is text-only — Groq's vision-capable models are a
    # separate, smaller lineup that churns fast: rag-backend/ (this project's
    # predecessor) used meta-llama/llama-4-scout-17b-16e-instruct as of
    # 2026-06, but by 2026-08 Groq had retired it (confirmed via a live 404
    # "model_not_found"). qwen/qwen3.6-27b is what console.groq.com/docs/
    # vision currently lists — if this starts 404ing too, that page has
    # whatever replaced it. Used only for complete_vision() (scanned PDF
    # pages, standalone images), never for text chat.
    groq_vision_model: str = "qwen/qwen3.6-27b"
    # Smaller/cheaper text model for mechanical tasks (concept tagging,
    # document classification, summaries, flashcard/quiz generation, RAG
    # query rewriting) — see llm/factory.py's build_simple_llm_provider.
    # Tutoring answers, exam-question grading, and other reasoning-heavy work
    # keep using groq_chat_model above.
    groq_simple_chat_model: str = "llama-3.1-8b-instant"

    openrouter_api_key: str = ""
    openrouter_chat_model: str = "google/gemini-2.0-flash-exp:free"
    # Empty means "reuse openrouter_chat_model for vision too" (many
    # OpenRouter models, including the default above, are already
    # multimodal) — only set this if that model stops supporting images.
    openrouter_vision_model: str = ""
    # Empty means "reuse openrouter_chat_model for simple tasks too" — unlike
    # Groq, OpenRouter's free-tier model roster changes too often to pick a
    # safe default; set this once you've settled on one.
    openrouter_simple_chat_model: str = ""

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    # Empty means "reuse openai_chat_model for vision too" — gpt-4o-mini is
    # natively multimodal, so this only needs setting if that changes.
    openai_vision_model: str = ""
    # Empty means "reuse openai_chat_model for simple tasks too" — gpt-4o-mini
    # is already the cheap tier, so there's less to gain here than on Groq.
    openai_simple_chat_model: str = ""

    anthropic_api_key: str = ""

    # File storage — local disk in development, swap for the S3 implementation
    # of the same StoragePort interface in production.
    storage_dir: str = "./uploads"
    max_upload_mb: int = 50

    # Re-uploading a file already ingested for the same subject (identical
    # sha256 of the raw bytes) returns the existing document instead of
    # reprocessing it — avoids burning API quota on accidental re-uploads.
    document_dedup_enabled: bool = True

    # Usage tracking (Phase-agnostic — architecture, not a paywall). Every
    # LLM/embedding call and every document processed is logged per-user via
    # UsageService regardless of these limits; the limits below are only
    # enforced when usage_limits_enabled is True. Off by default so existing
    # dev/test flows and the current single-tier product aren't affected —
    # flip it on once free/premium tiers actually exist.
    usage_limits_enabled: bool = False
    free_daily_ai_requests: int = 50
    free_daily_documents: int = 10

    # Chunking — character-based (no tokenizer dependency). Parent chunks keep
    # enough surrounding context for coherent concept tagging and citations;
    # child chunks are what gets embedded and retrieved for RAG precision.
    chunk_parent_chars: int = 900
    chunk_child_chars: int = 220
    chunk_overlap_chars: int = 40

    # Concept tagging. Runs as a background follow-up *after* a document is
    # marked ready (see ingestion_task.py) — it enriches the subject's
    # knowledge graph but nothing on the RAG-critical path depends on it.
    # Batched (concept_tag_batch_size chunks per LLM call, not one call per
    # chunk) since it's the ingestion step with the most chunks to process.
    concept_tag_relevance_threshold: float = 0.5
    max_new_concepts_per_chunk: int = 3
    concept_tag_batch_size: int = 6

    # Cloud-API concurrency/retry tuning — shared by every LLMProvider and
    # EmbeddingProvider implementation. Kept as env-configurable knobs (not
    # hardcoded) so a stricter/more generous provider tier can be dialed in
    # without a code change. Concurrency is bounded (never "fire N requests
    # at once with no cap") specifically to avoid the burst-429 pattern large
    # documents used to trigger.
    llm_max_concurrency: int = 3
    embedding_max_concurrency: int = 5
    embedding_batch_size: int = 100
    max_retries: int = 3
    initial_retry_delay: float = 15.0
    max_retry_delay: float = 90.0

    # Document classification (type + curriculum chapter/lesson placement).
    # Runs once per document on parent-chunk text, capped the same way
    # summary/flashcard/quiz source assembly is capped. Below the confidence
    # threshold the chapter/lesson match is dropped but document_type (a
    # forced choice, not a similarity match) is always kept.
    classification_max_source_chars: int = 6000
    classification_confidence_threshold: float = 0.5

    # RAG chat (Phase 4). Each technique is its own flag so a slower/cheaper
    # free-tier LLM can have some of them switched off without code changes.
    rag_enable_hyde: bool = True
    rag_enable_multi_query: bool = True
    rag_enable_rerank: bool = True
    rag_multi_query_count: int = 3          # extra query variations beyond the original + HyDE
    rag_retrieval_top_k: int = 8            # per query variant, before fusion
    rag_final_context_chunks: int = 6       # chunks kept after fusion/rerank, sent to the answer LLM
    rag_history_messages: int = 6           # prior turns fed into condense_question

    # Summary engine (Phase 5). A summary is scoped to one document, built from
    # that document's parent chunks (already-chosen context windows, no vector
    # search needed since the "corpus" is just this one document) rather than
    # through the RAG retriever — capped so a huge document doesn't blow past
    # free-tier context limits or turn a summary into an expensive call.
    summary_max_source_chars: int = 16000

    # Flashcard engine (Phase 6). Same document-scoped source assembly as
    # summaries (shared in services/knowledge_base/document_source.py);
    # generation count is caller-adjustable up to this cap so a request can't
    # accidentally ask for hundreds of cards in one (expensive) LLM call.
    flashcard_source_max_chars: int = 16000
    flashcard_default_generate_count: int = 10
    flashcard_max_generate_count: int = 30

    # Quiz + exam engine (Phase 7). Same document-scoped source assembly as
    # summaries/flashcards; open-ended answers (short_answer/calculation) are
    # graded via an extra LLM call per submission, so the generate cap here
    # also bounds grading cost per attempt.
    quiz_source_max_chars: int = 16000
    quiz_default_generate_count: int = 10
    quiz_max_generate_count: int = 30

    # Progress engine (Phase 8). Mastery/weak-concept thresholds are tuned
    # heuristics, not a fixed algorithm spec (unlike sm2.py) — kept
    # adjustable here rather than hardcoded so they can be tuned without a
    # code change as real usage data comes in.
    progress_trend_up_threshold: float = 1.0
    progress_trend_down_threshold: float = 1.0
    weak_concept_min_error_count: int = 2
    weak_concept_error_rate_threshold: float = 0.5
    weak_concept_slow_response_seconds: float = 60.0
    weak_concept_decay_drop_threshold: float = 15.0
    weak_concept_decay_min_previous_score: float = 60.0

    # Planning engine (Phase 9). Session length and default plan length (used
    # when no exam_date is given) are tuned heuristics, same reasoning as the
    # progress engine's thresholds above — adjustable without a code change.
    planning_default_session_minutes: int = 25
    planning_default_plan_days: int = 14

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.secret_key == "change-me-in-production":
        raise RuntimeError("SECRET_KEY must be set to a random value in production.")
    return settings


settings = get_settings()
