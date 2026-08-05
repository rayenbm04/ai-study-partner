"""Runs an open-source sentence-transformers model on the backend's own
CPU — no API key, no billing account on file, no network call at all once
the model weights are cached locally after first use. Exists because some
"free" cloud embedding tiers (Gemini's included) now require a billing
account to be linked even though the tier itself doesn't charge — a
dealbreaker for anyone who can't/won't add a card. This is the only
genuinely card-free option in the pipeline.
"""
import asyncio
import threading

from sentence_transformers import SentenceTransformer

from app.services.embeddings.base import EmbeddingProvider

# Loading model weights from disk takes real time (and the first call
# downloads them), so the model is cached process-wide keyed by name rather
# than reloaded per LocalEmbedder instance — instances are constructed fresh
# per request/ingestion call, same as the cloud providers, but the
# underlying model must not be.
_model_cache: dict[str, SentenceTransformer] = {}
_cache_lock = threading.Lock()


def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _model_cache:
        with _cache_lock:
            if model_name not in _model_cache:
                _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


class LocalEmbedder(EmbeddingProvider):
    def __init__(self, *, model_name: str, dimension: int):
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._encode, [text])
        return vectors[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        # Runs on a worker thread (see asyncio.to_thread above) — sentence-transformers'
        # .encode() is a blocking, CPU-bound call and would otherwise stall the event loop.
        model = _get_model(self._model_name)
        vectors = model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()
