"""Application settings, loaded from environment variables / .env.

Everything LLM-related is a cloud API key + model name — there is no local
inference anywhere in this pipeline (no Ollama, no on-disk model weights).
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

    # LLM providers (cloud-only). See docs/LLM_PROVIDERS.md.
    llm_provider: str = "gemini"          # gemini | groq | openrouter | openai
    embedding_provider: str = "gemini"    # gemini only, for now — see docs/LLM_PROVIDERS.md

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    # gemini-embedding-001 supports Matryoshka truncation up to 3072 dims; 768 is
    # Google's recommended quality/storage balance. Must match the pgvector
    # column width in the embeddings table migration if changed.
    embedding_dimension: int = 768

    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"

    openrouter_api_key: str = ""
    openrouter_chat_model: str = "google/gemini-2.0-flash-exp:free"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"

    anthropic_api_key: str = ""

    # File storage — local disk in development, swap for the S3 implementation
    # of the same StoragePort interface in production.
    storage_dir: str = "./uploads"
    max_upload_mb: int = 50

    # Chunking — character-based (no tokenizer dependency). Parent chunks keep
    # enough surrounding context for coherent concept tagging and citations;
    # child chunks are what gets embedded and retrieved for RAG precision.
    chunk_parent_chars: int = 900
    chunk_child_chars: int = 220
    chunk_overlap_chars: int = 40

    # Concept tagging
    concept_tag_relevance_threshold: float = 0.5
    max_new_concepts_per_chunk: int = 3

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
