from app.core.config import Settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.gemini_embedder import GeminiEmbedder
from app.services.embeddings.local_embedder import LocalEmbedder


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider

    if provider == "gemini":
        return GeminiEmbedder(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
            dimension=settings.embedding_dimension,
        )
    if provider == "local":
        return LocalEmbedder(model_name=settings.local_embedding_model, dimension=settings.embedding_dimension)

    raise ValueError(f"Unknown EMBEDDING_PROVIDER '{provider}'. Expected: gemini, local.")
