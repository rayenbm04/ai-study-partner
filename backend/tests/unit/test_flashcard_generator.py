import json

from app.domain.entities.concept import Concept
from app.services.flashcard_engine.generator import generate_flashcards
from tests.unit.fakes import FakeLLMProvider


def _concept(name: str) -> Concept:
    return Concept(id=f"concept-{name}", subject_id="subj-1", name=name, description=None, parent_concept_id=None)


async def test_generate_flashcards_parses_valid_response():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "flashcards": [
                    {"question": "What is Ohm's law?", "answer": "V = I * R", "difficulty": "easy",
                     "concept_name": None, "tags": ["circuits"]},
                ]
            }
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="ohms_law.pdf", source_text="Ohm's law text", concepts=[], count=1
    )

    assert len(drafts) == 1
    assert drafts[0].question == "What is Ohm's law?"
    assert drafts[0].answer == "V = I * R"
    assert drafts[0].difficulty == "easy"
    assert drafts[0].tags == ["circuits"]
    assert drafts[0].concept_id is None
    assert drafts[0].source == "generated"


async def test_generate_flashcards_resolves_matching_concept_name():
    concept = _concept("Ohm's Law")
    llm = FakeLLMProvider(
        response=json.dumps(
            {"flashcards": [{"question": "q", "answer": "a", "difficulty": "medium", "concept_name": "Ohm's Law", "tags": []}]}
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[concept], count=1
    )

    assert drafts[0].concept_id == concept.id


async def test_generate_flashcards_drops_unmatched_concept_name():
    concept = _concept("Ohm's Law")
    llm = FakeLLMProvider(
        response=json.dumps(
            {"flashcards": [{"question": "q", "answer": "a", "difficulty": "medium", "concept_name": "Nonexistent", "tags": []}]}
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[concept], count=1
    )

    assert drafts[0].concept_id is None  # no hallucinated concept linkage


async def test_generate_flashcards_defaults_invalid_difficulty_to_medium():
    llm = FakeLLMProvider(
        response=json.dumps(
            {"flashcards": [{"question": "q", "answer": "a", "difficulty": "impossible", "concept_name": None, "tags": []}]}
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=1
    )

    assert drafts[0].difficulty == "medium"


async def test_generate_flashcards_truncates_to_requested_count():
    llm = FakeLLMProvider(
        response=json.dumps(
            {"flashcards": [{"question": f"q{i}", "answer": f"a{i}", "difficulty": "easy", "concept_name": None, "tags": []} for i in range(5)]}
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=2
    )

    assert len(drafts) == 2


async def test_generate_flashcards_skips_cards_missing_question_or_answer():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "flashcards": [
                    {"question": "", "answer": "a", "difficulty": "easy", "concept_name": None, "tags": []},
                    {"question": "q", "answer": "", "difficulty": "easy", "concept_name": None, "tags": []},
                    {"question": "good q", "answer": "good a", "difficulty": "easy", "concept_name": None, "tags": []},
                ]
            }
        )
    )

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=3
    )

    assert len(drafts) == 1
    assert drafts[0].question == "good q"


async def test_generate_flashcards_returns_empty_on_bad_json():
    llm = FakeLLMProvider(response="not json")

    drafts = await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[], count=3
    )

    assert drafts == []


async def test_generate_flashcards_returns_empty_when_llm_raises():
    class BoomLLM(FakeLLMProvider):
        async def complete(self, **kwargs):
            raise RuntimeError("provider down")

    drafts = await generate_flashcards(
        llm_provider=BoomLLM(), document_filename="doc.pdf", source_text="text", concepts=[], count=3
    )

    assert drafts == []


async def test_generate_flashcards_prompt_includes_count_and_concepts():
    concept = _concept("Inertia")
    llm = FakeLLMProvider(response=json.dumps({"flashcards": []}))

    await generate_flashcards(
        llm_provider=llm, document_filename="doc.pdf", source_text="text", concepts=[concept], count=7
    )

    assert "7" in llm.calls[0]["system"]
    assert "Inertia" in llm.calls[0]["prompt"]
