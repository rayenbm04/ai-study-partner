"""Embeds text through Gemini's embedding API.

Unlike the chat/vision provider, embedding requests during ingestion can
number in the thousands for a single large document (one per child chunk) —
sending them all in one API call risks hitting the provider's per-request
payload/item limit, and doing them one-by-one is both slow and, without
retry, fragile (a single transient 429 used to fail the whole ingestion).
This batches the input into `batch_size`-sized groups and runs them
concurrently, bounded by `max_concurrency`, each wrapped in the same
bounded retry-on-429 helper every LLM call already uses.
"""
import asyncio
import logging

from google import genai
from google.genai import types

from app.services.embeddings.base import EmbeddingProvider
from app.services.llm.gemini_errors import is_daily_quota_exhausted, is_rate_limit_error, parse_retry_delay
from app.services.llm.rate_limit_retry import retry_on_rate_limit

logger = logging.getLogger(__name__)


class GeminiEmbedder(EmbeddingProvider):
    def __init__(
        self, *, api_key: str, model: str, dimension: int, batch_size: int = 100, max_concurrency: int = 5
    ):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimension = dimension
        self._batch_size = max(1, batch_size)
        self._max_concurrency = max(1, max_concurrency)
        # Bounds how many embedding batches are in flight at once — the same
        # "controlled concurrency, not hundreds of simultaneous calls"
        # principle applied to LLM calls, applied here to embedding calls.
        self._semaphore = asyncio.Semaphore(self._max_concurrency)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        async def call():
            return await self._client.aio.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=self._dimension),
            )

        async with self._semaphore:
            response = await retry_on_rate_limit(
                call,
                is_rate_limit_error=is_rate_limit_error,
                parse_retry_delay=parse_retry_delay,
                provider_name="Gemini embeddings",
                is_unrecoverable=is_daily_quota_exhausted,
            )
        return [embedding.values for embedding in response.embeddings]

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        batches = [texts[i : i + self._batch_size] for i in range(0, len(texts), self._batch_size)]
        if len(batches) > 1:
            logger.info(
                "Embedding %d texts in %d batches (batch_size=%d, max_concurrency=%d)",
                len(texts), len(batches), self._batch_size, self._max_concurrency,
            )
        # Batches run concurrently (bounded by the semaphore above) — each is
        # a pure network call with no shared state, so out-of-order
        # completion is safe as long as results are reassembled by
        # submission order, which gather() guarantees.
        results = await asyncio.gather(*(self._embed_batch(batch, task_type) for batch in batches))
        return [vector for batch_result in results for vector in batch_result]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]
