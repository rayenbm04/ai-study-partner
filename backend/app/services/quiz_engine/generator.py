"""Generates quiz questions from a document's source material via one
structured JSON LLM call — same "read the source text, ground concept
references in the graph, parse defensively" pattern as the flashcard and
summary generators (services/flashcard_engine/generator.py,
services/summary_engine/summary_service.py).

Concept resolution is deliberately conservative, matching the flashcard
generator: the LLM is given the concepts already tagged to this document and
asked to reference one by exact name if a question clearly tests it, but a
name that doesn't match anything in that list is dropped (concept_id=None)
rather than creating a new concept.

Per-type validation happens here (not left to the LLM's word) since a broken
mcq (no options, or a correct_answer that isn't one of the options) or a
malformed true_false answer would silently break grading later — any
question that doesn't pass validation for its stated type is dropped rather
than persisted in a broken state.
"""
import json
import logging

from app.domain.entities.concept import Concept
from app.domain.entities.quiz import DIFFICULTIES, QUESTION_TYPES, QuizQuestionDraft
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You write quiz questions from course material for student self-assessment. Respond with strict "
    'JSON only, matching this shape: {"questions": [{"type": "mcq|true_false|short_answer|calculation|'
    'fill_blank", "question": "<the question text>", "options": ["<choice>", ...] or null, '
    '"correct_answer": "<the correct answer>", "explanation": "<why this is correct, shown to the '
    'student after grading>", "points": <integer 1-5>, "difficulty": "easy|medium|hard", '
    '"concept_name": "<name from the provided concept list this question tests, or null>"}, ...]}. '
    "Generate exactly __COUNT__ questions, using only these question types: __TYPES__. For 'mcq', "
    "options must contain 3-5 plausible choices with exactly one correct, and correct_answer must be "
    "the exact text of one of those options. Never use 'All of the above', 'None of the above', or "
    "any other option that refers to the other options collectively — write one specific, "
    "self-contained correct option instead; if several factors are all correct, ask about one of "
    "them specifically or combine them into a single specific option's text rather than bundling "
    "them behind a referential choice. For 'true_false', options must be null and correct_answer "
    "must be exactly 'true' or 'false'. For 'short_answer', 'calculation', and 'fill_blank', options "
    "must be null and correct_answer is the expected answer written out in full. Target difficulty: "
    "__DIFFICULTY__, but vary individual questions around it. Only set concept_name to a name that "
    "appears verbatim in the provided concept list; use null if no concept in that list fits, or if "
    "the list is empty."
)


def _format_concepts(concepts: list[Concept]) -> str:
    if not concepts:
        return "(No concepts have been tagged to this document yet.)"
    return "\n".join(f"- {c.name}" for c in concepts)


# Referential options ("All of the above") are a poor fit for these
# auto-generated, non-reviewed quizzes: some client UIs render mcq as
# single-select, and the option text alone often isn't enough to tell a
# student which of the *other* options it's referring to once options are
# reordered/rephrased. The system prompt already discourages this; dropping
# any question that slips through anyway (rather than silently persisting
# it) is the same "broken question -> drop, don't persist" policy this
# module already applies to malformed mcq/true_false questions.
_REFERENTIAL_ANSWER_MARKERS = ("all of the above", "none of the above", "both a and b", "all the above")


def _is_referential_answer(text: str) -> bool:
    lowered = text.strip().lower()
    return any(marker in lowered for marker in _REFERENTIAL_ANSWER_MARKERS)


def _normalize_true_false(value: str) -> str | None:
    lowered = value.strip().lower()
    if lowered in ("true", "false"):
        return lowered
    return None


def _validate_and_build(raw: dict, allowed_types: set[str], concepts_by_name: dict[str, Concept]) -> QuizQuestionDraft | None:
    try:
        question_type = str(raw["type"]).strip().lower()
        question_text = str(raw["question"]).strip()
        correct_answer = str(raw["correct_answer"]).strip()
    except (KeyError, TypeError):
        return None
    if question_type not in QUESTION_TYPES or question_type not in allowed_types:
        return None
    if not question_text or not correct_answer:
        return None
    if question_type == "mcq" and _is_referential_answer(correct_answer):
        return None

    raw_options = raw.get("options")
    options: list[str] | None = None
    if question_type == "mcq":
        if not isinstance(raw_options, list):
            return None
        options = [str(o).strip() for o in raw_options if str(o).strip()]
        if len(options) < 2 or correct_answer not in options:
            return None
    elif question_type == "true_false":
        normalized = _normalize_true_false(correct_answer)
        if normalized is None:
            return None
        correct_answer = normalized
    # short_answer / calculation / fill_blank: options stays None, correct_answer as given.

    difficulty = str(raw.get("difficulty", "medium")).strip().lower()
    if difficulty not in DIFFICULTIES:
        difficulty = "medium"

    try:
        points = int(raw.get("points", 1))
    except (TypeError, ValueError):
        points = 1
    points = max(1, min(points, 5))

    explanation = raw.get("explanation")
    explanation = str(explanation).strip() if explanation else None

    concept_name = raw.get("concept_name")
    concept = concepts_by_name.get(str(concept_name).strip()) if concept_name else None

    return QuizQuestionDraft(
        type=question_type,
        question=question_text,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation,
        points=points,
        difficulty=difficulty,
        concept_id=concept.id if concept else None,
    )


async def generate_quiz_questions(
    *,
    llm_provider: LLMProvider,
    document_filename: str,
    source_text: str,
    concepts: list[Concept],
    count: int,
    question_types: list[str],
    difficulty: str,
) -> list[QuizQuestionDraft]:
    allowed_types = set(question_types) & set(QUESTION_TYPES)
    if not allowed_types:
        allowed_types = set(QUESTION_TYPES)

    system = (
        _SYSTEM_PROMPT.replace("__COUNT__", str(count))
        .replace("__TYPES__", ", ".join(sorted(allowed_types)))
        .replace("__DIFFICULTY__", difficulty)
    )
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
        raw_questions = parsed["questions"] if isinstance(parsed, dict) else None
        if not isinstance(raw_questions, list):
            raise ValueError("questions missing or not a list")
    except Exception:
        logger.exception("Quiz generation LLM call failed or returned unusable JSON")
        return []

    drafts: list[QuizQuestionDraft] = []
    for raw in raw_questions[:count]:
        if not isinstance(raw, dict):
            continue
        draft = _validate_and_build(raw, allowed_types, concepts_by_name)
        if draft is not None:
            drafts.append(draft)

    return drafts
