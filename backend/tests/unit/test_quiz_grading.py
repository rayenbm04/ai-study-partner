import json

from app.domain.entities.quiz import QuizQuestion
from app.services.quiz_engine.grading import grade_objective, grade_open_ended
from tests.unit.fakes import FakeLLMProvider


def _question(**overrides) -> QuizQuestion:
    base = dict(
        id="q-1", quiz_id="quiz-1", concept_id=None, type="mcq", question="What is Ohm's law?",
        options=["V = I * R", "V = I + R"], correct_answer="V = I * R", explanation="...", points=1,
        difficulty="easy",
    )
    base.update(overrides)
    return QuizQuestion(**base)


def test_grade_objective_mcq_exact_match():
    question = _question(type="mcq", correct_answer="V = I * R")
    assert grade_objective(question, "V = I * R") is True
    assert grade_objective(question, "V = I + R") is False


def test_grade_objective_mcq_ignores_case_and_whitespace():
    question = _question(type="mcq", correct_answer="Paris")
    assert grade_objective(question, "  paris  ") is True


def test_grade_objective_true_false():
    question = _question(type="true_false", options=None, correct_answer="true")
    assert grade_objective(question, "True") is True
    assert grade_objective(question, "false") is False


def test_grade_objective_fill_blank_normalizes_whitespace():
    question = _question(type="fill_blank", options=None, correct_answer="mitochondria")
    assert grade_objective(question, "  Mitochondria ") is True


def test_grade_objective_true_false_accepts_yes_no_synonyms():
    """A Yes/No toggle is a reasonable true_false UI even though
    correct_answer is always literally "true"/"false" — see generator.py's
    _normalize_true_false."""
    question = _question(type="true_false", options=None, correct_answer="false")
    assert grade_objective(question, "no") is True
    assert grade_objective(question, "No") is True
    assert grade_objective(question, "yes") is False

    question = _question(type="true_false", options=None, correct_answer="true")
    assert grade_objective(question, "yes") is True
    assert grade_objective(question, "Y") is True


def test_grade_objective_true_false_rejects_unrecognized_answer():
    question = _question(type="true_false", options=None, correct_answer="true")
    assert grade_objective(question, "maybe") is False


def test_grade_objective_fill_blank_tolerates_comma_decimal_separator():
    """A European-locale keyboard typing a numeric fill-in-the-blank answer
    commonly uses a comma decimal separator ("6,67") — that's the same
    number as the period-separated reference answer ("6.67"), not a wrong
    answer."""
    question = _question(type="fill_blank", options=None, correct_answer="6.67")
    assert grade_objective(question, "6,67") is True
    assert grade_objective(question, "6.67") is True
    assert grade_objective(question, "6,68") is False


def test_grade_objective_fill_blank_non_numeric_still_requires_exact_match():
    question = _question(type="fill_blank", options=None, correct_answer="mitochondria")
    assert grade_objective(question, "nucleus") is False


def test_grade_objective_returns_none_for_short_answer():
    question = _question(type="short_answer", options=None, correct_answer="anything")
    assert grade_objective(question, "anything") is None


def test_grade_objective_returns_none_for_calculation():
    question = _question(type="calculation", options=None, correct_answer="42")
    assert grade_objective(question, "42") is None


async def test_grade_open_ended_reads_llm_verdict():
    question = _question(type="short_answer", options=None, correct_answer="Newton's second law")
    llm = FakeLLMProvider(response=json.dumps({"is_correct": True}))

    result = await grade_open_ended(llm_provider=llm, question=question, answer="F = ma, Newton's 2nd law")

    assert result is True
    assert "Newton's second law" in llm.calls[0]["prompt"]


async def test_grade_open_ended_false_verdict():
    question = _question(type="short_answer", options=None, correct_answer="42")
    llm = FakeLLMProvider(response=json.dumps({"is_correct": False}))

    result = await grade_open_ended(llm_provider=llm, question=question, answer="wrong")

    assert result is False


async def test_grade_open_ended_fails_closed_on_bad_json():
    question = _question(type="short_answer", options=None, correct_answer="42")
    llm = FakeLLMProvider(response="not json")

    result = await grade_open_ended(llm_provider=llm, question=question, answer="42")

    assert result is False


async def test_grade_open_ended_fails_closed_when_llm_raises():
    class BoomLLM(FakeLLMProvider):
        async def complete(self, **kwargs):
            raise RuntimeError("provider down")

    question = _question(type="short_answer", options=None, correct_answer="42")
    result = await grade_open_ended(llm_provider=BoomLLM(), question=question, answer="42")

    assert result is False
