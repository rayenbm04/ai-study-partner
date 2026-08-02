"""Turns a raw student question (plus recent chat history) into a set of
search queries that retrieve better than the raw question alone would:

- condense_question: rewrites a follow-up ("what about the second one?") into
  a standalone question using the conversation history, so retrieval doesn't
  have to guess what "the second one" refers to.
- expand_query: in one structured LLM call, generates a HyDE hypothetical
  answer (embedding a plausible answer tends to land closer to the real
  supporting passages than embedding the question itself) and a handful of
  reworded variations of the question (multi-query expansion) — combined into
  one call instead of two/three separate ones to keep latency and free-tier
  quota usage down.

Every technique here is a config flag (settings.rag_enable_hyde /
rag_enable_multi_query) so a slower or stricter free-tier model can have them
switched off without touching this code.
"""
import json
import logging

from app.domain.entities.message import Message
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_CONDENSE_SYSTEM_PROMPT = (
    "You rewrite a student's latest chat message into a standalone question that makes "
    "sense without the conversation history, resolving pronouns and implicit references "
    "(e.g. 'the second one', 'that formula') using the history. If the latest message is "
    "already standalone, return it unchanged. Respond with the rewritten question as plain "
    "text only — no quotes, no explanation."
)

_EXPAND_SYSTEM_PROMPT_TEMPLATE = (
    "You help retrieve study material for a student's question. Respond with strict JSON only, "
    'matching this shape: {"hypothetical_answer": "<a plausible, concise answer to the question, '
    "as if written in a textbook — used only to improve semantic search, doesn't need to be "
    'correct>", "variations": ["<reworded version of the question>", ...]}. Generate exactly '
    "__COUNT__ variations, each phrasing the same underlying question differently (different "
    "terminology, more/less specific) so a vector search catches passages the original phrasing "
    "might miss. Do not answer the question itself outside of hypothetical_answer."
)


async def condense_question(
    *, llm_provider: LLMProvider, question: str, history: list[Message]
) -> str:
    """Returns `question` unchanged if there's no history to disambiguate against."""
    if not history:
        return question

    transcript = "\n".join(f"{m.role}: {m.content}" for m in history)
    prompt = f"Conversation so far:\n{transcript}\n\nLatest message: {question}"

    try:
        rewritten = await llm_provider.complete(
            system=_CONDENSE_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.0,
            max_output_tokens=200,
        )
    except Exception:
        logger.exception("condense_question LLM call failed, falling back to raw question")
        return question

    rewritten = rewritten.strip().strip('"')
    return rewritten or question


class QueryExpansion:
    """hypothetical_answer is None when HyDE is disabled or the LLM call
    failed; variations is always a list (possibly empty)."""

    __slots__ = ("hypothetical_answer", "variations")

    def __init__(self, *, hypothetical_answer: str | None, variations: list[str]):
        self.hypothetical_answer = hypothetical_answer
        self.variations = variations


async def expand_query(
    *,
    llm_provider: LLMProvider,
    question: str,
    enable_hyde: bool,
    enable_multi_query: bool,
    variation_count: int,
) -> QueryExpansion:
    if not enable_hyde and not enable_multi_query:
        return QueryExpansion(hypothetical_answer=None, variations=[])

    count = variation_count if enable_multi_query else 0
    system = _EXPAND_SYSTEM_PROMPT_TEMPLATE.replace("__COUNT__", str(count))
    try:
        response_text = await llm_provider.complete(
            system=system,
            prompt=f"Question: {question}",
            temperature=0.3,
            response_json=True,
        )
        parsed = json.loads(response_text)
    except Exception:
        logger.exception("expand_query LLM call failed, falling back to no expansion")
        return QueryExpansion(hypothetical_answer=None, variations=[])

    if not isinstance(parsed, dict):
        return QueryExpansion(hypothetical_answer=None, variations=[])

    hypothetical_answer = None
    if enable_hyde:
        raw = parsed.get("hypothetical_answer")
        hypothetical_answer = str(raw).strip() if raw else None

    variations: list[str] = []
    if enable_multi_query:
        for item in (parsed.get("variations", []) or [])[:variation_count]:
            text = str(item).strip()
            if text:
                variations.append(text)

    return QueryExpansion(hypothetical_answer=hypothetical_answer, variations=variations)
