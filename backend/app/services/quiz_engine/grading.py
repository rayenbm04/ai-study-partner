"""Grading logic, split by question type.

mcq/true_false/fill_blank are graded by exact (whitespace/case-normalized)
string match against correct_answer, with two narrow, type-specific
tolerances (see _normalize_true_false_answer and _numeric_equal below) —
cheap, deterministic, no LLM call. short_answer/calculation are open-ended
enough that exact match would fail correct-but-differently-phrased answers,
so those go through one LLM call that judges substantive equivalence. If
that call fails, we fail closed (mark incorrect) rather than silently
awarding points on a broken response.
"""
import json
import logging

from app.domain.entities.quiz import QuizQuestion
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_GRADE_SYSTEM_PROMPT = (
    "You grade a student's answer to a quiz question against a reference answer. Respond with strict "
    'JSON only: {"is_correct": true|false}. Consider the answer correct if it is substantively '
    "equivalent to the reference answer even when phrased differently, or — for calculations — "
    "expressed in an equivalent numeric or algebraic form; minor rounding or formatting differences "
    "should not count against the student. An answer that is missing, off-topic, or contradicts the "
    "reference answer is incorrect."
)

# generator.py's _normalize_true_false guarantees correct_answer is always
# the literal "true"/"false" for this question type — but the client UI
# submitting the student's answer isn't guaranteed to send that same literal
# wording (a Yes/No toggle, or a localized label, are both reasonable UIs
# for a true/false question). Treat the common synonyms as equivalent rather
# than failing a semantically correct answer on wording alone.
_TRUE_FALSE_SYNONYMS: dict[str, str] = {
    "true": "true", "t": "true", "yes": "true", "y": "true", "vrai": "true", "1": "true",
    "false": "false", "f": "false", "no": "false", "n": "false", "faux": "false", "0": "false",
}


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _normalize_true_false_answer(text: str) -> str | None:
    return _TRUE_FALSE_SYNONYMS.get(_normalize(text))


def _numeric_equal(a: str, b: str) -> bool:
    """Compares two answer strings as numbers when possible, tolerating a
    comma decimal separator on either side (e.g. "6,67" vs "6.67" — a French/
    European locale keyboard typing a fill-in-the-blank numeric answer is a
    real, common case, not a student error). Returns False (not a numeric
    tolerance match) rather than raising when either side isn't a plain
    number, so grade_objective falls through to reporting incorrect."""
    try:
        return float(a.replace(",", ".")) == float(b.replace(",", "."))
    except ValueError:
        return False


def grade_objective(question: QuizQuestion, answer: str) -> bool | None:
    """Returns True/False for auto-gradable types, or None if this question's
    type needs the LLM-based grader in grade_open_ended()."""
    if question.type not in ("mcq", "true_false", "fill_blank"):
        return None

    normalized_answer = _normalize(answer)
    normalized_correct = _normalize(question.correct_answer)
    if normalized_answer == normalized_correct:
        return True

    if question.type == "true_false":
        return _normalize_true_false_answer(answer) == normalized_correct
    if question.type == "fill_blank":
        return _numeric_equal(normalized_answer, normalized_correct)
    return False  # mcq: options are presented verbatim, so exact match is the correct standard


async def grade_open_ended(*, llm_provider: LLMProvider, question: QuizQuestion, answer: str) -> bool:
    prompt = (
        f"Question: {question.question}\n"
        f"Reference answer: {question.correct_answer}\n"
        f"Student answer: {answer}"
    )
    try:
        response_text = await llm_provider.complete(
            system=_GRADE_SYSTEM_PROMPT, prompt=prompt, temperature=0.0, response_json=True, max_output_tokens=256
        )
        parsed = json.loads(response_text)
        return bool(parsed.get("is_correct", False))
    except Exception:
        logger.exception("Open-ended grading LLM call failed or returned unusable JSON")
        return False
