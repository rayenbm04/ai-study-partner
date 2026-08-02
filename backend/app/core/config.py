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
