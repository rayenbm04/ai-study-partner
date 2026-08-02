"""Grading logic, split by question type.

mcq/true_false/fill_blank are graded by exact (whitespace/case-normalized)
string match against correct_answer — cheap, deterministic, no LLM call.
short_answer/calculation are open-ended enough that exact match would fail
correct-but-differently-phrased answers, so those go through one LLM call
that judges substantive equivalence. If that call fails, we fail closed
(mark incorrect) rather than silently awarding points on a broken response.
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


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def grade_objective(question: QuizQuestion, answer: str) -> bool | None:
    """Returns True/False for auto-gradable types, or None if this question's
    type needs the LLM-based grader in grade_open_ended()."""
    if question.type in ("mcq", "true_false", "fill_blank"):
        return _normalize(answer) == _normalize(question.correct_answer)
    return None


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
