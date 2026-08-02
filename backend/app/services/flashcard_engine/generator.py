"""Generates flashcards from a document's source material via one structured
JSON LLM call — same "read the source text, ground concept references in the
graph, parse defensively" pattern as concept_tagger.py and summary_service.py.

Concept resolution is deliberately conservative: the LLM is given the list of
concepts already tagged to this document and asked to reference one by exact
name if a card clearly tests it, but a name that doesn't match anything in
that list is dropped (concept_id=None) rather than creating a new concept —
flashcard generation isn't the place new nodes get added to the graph.
"""
import json
import logging

from app.domain.entities.concept import Concept
from app.domain.entities.flashcard import DIFFICULTIES, FlashcardDraft
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You write flashcards for spaced-repetition study from course material. Respond with strict "
    'JSON only, matching this shape: {"flashcards": [{"question": "<a focused question testing one '
    'idea>", "answer": "<the answer, concise but complete>", "difficulty": "easy|medium|hard", '
    '"concept_name": "<name from the provided concept list this card tests, or null>", '
    '"tags": ["<short topic tag>", ...]}, ...]}. Generate exactly __COUNT__ flashcards. Each '
    "question should test one specific, checkable fact or idea — not a vague 'explain everything' "
    "prompt. Vary difficulty across the set. Only set concept_name to a name that appears verbatim "
    "in the provided concept list; use null if no concept in that list fits, or if the list is empty."
)


def _format_concepts(concepts: list[Concept]) -> str:
    if not concepts:
        return "(No concepts have been tagged to this document yet.)"
    return "\n".join(f"- {c.name}" for c in concepts)


async def generate_flashcards(
    *, llm_provider: LLMProvider, document_filename: str, source_text: str, concepts: list[Concept], count: int
) -> list[FlashcardDraft]:
    system = _SYSTEM_PROMPT.replace("__COUNT__", str(count))
    concepts_by_name = {c.name: c for c in concepts}
    prompt = (
        f"Document: {document_filename}\n\n"
        f"Concepts already tagged to this document:\n{_format_concepts(concepts)}\n\n"
        f'Source material:\n"""\n{source_text}\n"""'
    )

    try:
        response_text = await llm_provider.complete(
            system=system, prompt=prompt, temperature=0.4, response_json=True, max_output_tokens=4096
        )
        parsed = json.loads(response_text)
        raw_cards = parsed["flashcards"] if isinstance(parsed, dict) else None
        if not isinstance(raw_cards, list):
            raise ValueError("flashcards missing or not a list")
    except Exception:
        logger.exception("Flashcard generation LLM call failed or returned unusable JSON")
        return []

    drafts: list[FlashcardDraft] = []
    for card in raw_cards[:count]:
        try:
            question = str(card["question"]).strip()
            answer = str(card["answer"]).strip()
        except (KeyError, TypeError):
            continue
        if not question or not answer:
            continue

        difficulty = str(card.get("difficulty", "medium")).strip().lower()
        if difficulty not in DIFFICULTIES:
            difficulty = "medium"

        concept_name = card.get("concept_name")
        concept = concepts_by_name.get(str(concept_name).strip()) if concept_name else None

        tags = [str(t).strip() for t in (card.get("tags") or []) if str(t).strip()]

        drafts.append(
            FlashcardDraft(
                question=question,
                answer=answer,
                difficulty=difficulty,
                tags=tags,
                concept_id=concept.id if concept else None,
                source="generated",
            )
        )

    return drafts
