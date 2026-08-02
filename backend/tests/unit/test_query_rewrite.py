import json

from app.domain.entities.message import Message
from app.services.rag.query_rewrite import condense_question, expand_query
from tests.unit.fakes import FakeLLMProvider


def _message(role: str, content: str) -> Message:
    return Message(id="m1", conversation_id="c1", role=role, content=content, citations=[], created_at=None)


async def test_condense_question_returns_raw_question_when_no_history():
    llm = FakeLLMProvider(response="should not be used")

    result = await condense_question(llm_provider=llm, question="what about derivatives?", history=[])

    assert result == "what about derivatives?"
    assert llm.calls == []


async def test_condense_question_uses_llm_rewrite_with_history():
    llm = FakeLLMProvider(response="What is the derivative of x^2?")
    history = [_message("user", "Let's talk about calculus"), _message("assistant", "Sure, what about it?")]

    result = await condense_question(llm_provider=llm, question="what's its derivative", history=history)

    assert result == "What is the derivative of x^2?"
    assert "Let's talk about calculus" in llm.calls[0]["prompt"]


async def test_condense_question_falls_back_to_raw_question_on_llm_failure():
    class BoomLLM(FakeLLMProvider):
        async def complete(self, **kwargs):
            raise RuntimeError("provider down")

    history = [_message("user", "hi")]
    result = await condense_question(llm_provider=BoomLLM(), question="what about it?", history=history)

    assert result == "what about it?"


async def test_expand_query_returns_empty_when_both_disabled():
    llm = FakeLLMProvider(response="should not be called")

    expansion = await expand_query(
        llm_provider=llm, question="q", enable_hyde=False, enable_multi_query=False, variation_count=3
    )

    assert expansion.hypothetical_answer is None
    assert expansion.variations == []
    assert llm.calls == []


async def test_expand_query_parses_hyde_and_variations():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "hypothetical_answer": "The derivative of x^2 is 2x.",
                "variations": ["derivative of x squared", "how to differentiate x^2", "d/dx x^2"],
            }
        )
    )

    expansion = await expand_query(
        llm_provider=llm, question="what is d/dx x^2", enable_hyde=True, enable_multi_query=True, variation_count=3
    )

    assert expansion.hypothetical_answer == "The derivative of x^2 is 2x."
    assert expansion.variations == ["derivative of x squared", "how to differentiate x^2", "d/dx x^2"]


async def test_expand_query_respects_hyde_only():
    llm = FakeLLMProvider(
        response=json.dumps({"hypothetical_answer": "answer text", "variations": ["v1", "v2"]})
    )

    expansion = await expand_query(
        llm_provider=llm, question="q", enable_hyde=True, enable_multi_query=False, variation_count=3
    )

    assert expansion.hypothetical_answer == "answer text"
    assert expansion.variations == []


async def test_expand_query_truncates_variations_to_requested_count():
    llm = FakeLLMProvider(
        response=json.dumps({"hypothetical_answer": None, "variations": ["v1", "v2", "v3", "v4", "v5"]})
    )

    expansion = await expand_query(
        llm_provider=llm, question="q", enable_hyde=False, enable_multi_query=True, variation_count=2
    )

    assert expansion.variations == ["v1", "v2"]


async def test_expand_query_falls_back_gracefully_on_bad_json():
    llm = FakeLLMProvider(response="not json at all")

    expansion = await expand_query(
        llm_provider=llm, question="q", enable_hyde=True, enable_multi_query=True, variation_count=3
    )

    assert expansion.hypothetical_answer is None
    assert expansion.variations == []
