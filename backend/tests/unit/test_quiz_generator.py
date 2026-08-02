import json

from app.domain.entities.concept import Concept
from app.services.quiz_engine.generator import generate_quiz_questions
from tests.unit.fakes import FakeLLMProvider


def _concept(name: str) -> Concept:
    return Concept(id=f"concept-{name}", subject_id="subj-1", name=name, description=None, parent_concept_id=None)


def _question(**overrides) -> dict:
    base = {
        "type": "mcq",
        "question": "What is Ohm's law?",
        "options": ["V = I * R", "V = I + R", "V = I / R"],
        "correct_answer": "V = I * R",
        "explanation": "Voltage equals current times resistance.",
        "points": 2,
        "difficulty": "easy",
        "concept_name": None,
    }
    base.update(overrides)
    return base


async def test_generate_quiz_questions_parses_valid_mcq():
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question()]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert len(drafts) == 1
    assert drafts[0].type == "mcq"
    assert drafts[0].options == ["V = I * R", "V = I + R", "V = I / R"]
    assert drafts[0].correct_answer == "V = I * R"
    assert drafts[0].points == 2


async def test_generate_quiz_questions_rejects_mcq_with_correct_answer_not_in_options():
    bad = _question(correct_answer="Not an option")
    llm = FakeLLMProvider(response=json.dumps({"questions": [bad]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_rejects_mcq_with_too_few_options():
    bad = _question(options=["only one"])
    llm = FakeLLMProvider(response=json.dumps({"questions": [bad]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_normalizes_true_false_answer():
    tf = _question(type="true_false", options=None, correct_answer="TRUE")
    llm = FakeLLMProvider(response=json.dumps({"questions": [tf]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["true_false"], difficulty="easy",
    )

    assert drafts[0].correct_answer == "true"
    assert drafts[0].options is None


async def test_generate_quiz_questions_rejects_true_false_with_invalid_answer():
    tf = _question(type="true_false", options=None, correct_answer="maybe")
    llm = FakeLLMProvider(response=json.dumps({"questions": [tf]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["true_false"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_accepts_short_answer_without_options():
    sa = _question(type="short_answer", options=None, correct_answer="Voltage equals current times resistance")
    llm = FakeLLMProvider(response=json.dumps({"questions": [sa]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["short_answer"], difficulty="medium",
    )

    assert len(drafts) == 1
    assert drafts[0].options is None


async def test_generate_quiz_questions_drops_question_type_not_requested():
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question(type="mcq")]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["true_false"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_resolves_matching_concept_name():
    concept = _concept("Ohm's Law")
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question(concept_name="Ohm's Law")]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[concept], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts[0].concept_id == concept.id


async def test_generate_quiz_questions_drops_unmatched_concept_name():
    concept = _concept("Ohm's Law")
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question(concept_name="Nonexistent")]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[concept], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts[0].concept_id is None


async def test_generate_quiz_questions_clamps_points_to_valid_range():
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question(points=99)]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts[0].points == 5


async def test_generate_quiz_questions_defaults_invalid_difficulty_to_medium():
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question(difficulty="impossible")]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts[0].difficulty == "medium"


async def test_generate_quiz_questions_truncates_to_requested_count():
    llm = FakeLLMProvider(response=json.dumps({"questions": [_question() for _ in range(5)]}))

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=2,
        question_types=["mcq"], difficulty="easy",
    )

    assert len(drafts) == 2


async def test_generate_quiz_questions_returns_empty_on_bad_json():
    llm = FakeLLMProvider(response="not json")

    drafts = await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=3,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_returns_empty_when_llm_raises():
    class BoomLLM(FakeLLMProvider):
        async def complete(self, **kwargs):
            raise RuntimeError("provider down")

    drafts = await generate_quiz_questions(
        llm_provider=BoomLLM(), document_filename="doc.pdf", source_text="text", concepts=[], count=3,
        question_types=["mcq"], difficulty="easy",
    )

    assert drafts == []


async def test_generate_quiz_questions_prompt_includes_count_and_types():
    llm = FakeLLMProvider(response=json.dumps({"questions": []}))

    await generate_quiz_questions(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=7,
        question_types=["mcq", "true_false"], difficulty="hard",
    )

    system = llm.calls[0]["system"]
    assert "7" in system
    assert "mcq" in system and "true_false" in system
    assert "hard" in system
