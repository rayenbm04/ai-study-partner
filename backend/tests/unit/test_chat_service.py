import json

import pytest

from app.core.exceptions import ConversationNotFoundError, SubjectNotFoundError
from app.domain.entities.chunk import ChunkDraft
from app.services.rag.chat_service import ChatService
from app.services.subject_service import SubjectService
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConversationRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeEmbeddingRepository,
    FakeLLMProvider,
    FakeMessageRepository,
    FakeSubjectRepository,
)


async def _build_chat_service(
    *, llm, enable_hyde=False, enable_multi_query=False, enable_rerank=False, final_context_chunks=3
):
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    chunk_repo = FakeChunkRepository()
    document_repo = FakeDocumentRepository()
    embedding_repo = FakeEmbeddingRepository(chunk_repo=chunk_repo)
    embedding_provider = FakeEmbeddingProvider(dimension=8)
    conversation_repo = FakeConversationRepository()
    message_repo = FakeMessageRepository()

    service = ChatService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        chunk_repo=chunk_repo,
        document_repo=document_repo,
        embedding_repo=embedding_repo,
        embedding_provider=embedding_provider,
        llm_provider=llm,
        subject_service=subject_service,
        enable_hyde=enable_hyde,
        enable_multi_query=enable_multi_query,
        enable_rerank=enable_rerank,
        multi_query_count=2,
        retrieval_top_k=5,
        final_context_chunks=final_context_chunks,
        history_messages=6,
    )
    return service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider


async def _seed_document_and_chunks(*, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider, user_id):
    subject = await subject_repo.create(user_id=user_id, name="Calculus", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="calc101.pdf",
        storage_path="x", file_type="pdf",
    )
    drafts = [
        ChunkDraft(
            content="Derivatives measure the rate of change of a function.", chunk_type="parent",
            parent_index=None, page=3, section_title="Ch1", chapter=None, token_count=8,
        ),
        ChunkDraft(
            content="The derivative of x^2 is 2x.", chunk_type="child", parent_index=0, page=3,
            section_title="Ch1", chapter=None, token_count=7,
        ),
    ]
    chunks = await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    child = next(c for c in chunks if c.chunk_type == "child")
    vector = await embedding_provider.embed_documents([child.content])
    await embedding_repo.bulk_create(chunk_ids=[child.id], vectors=vector, model_name=embedding_provider.model_name)
    return subject, document, child


async def test_send_message_answers_from_retrieved_context_and_records_citations():
    llm = FakeLLMProvider(response="The derivative of x^2 is 2x [1].")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject, document, child = await _seed_document_and_chunks(
        subject_repo=subject_repo, chunk_repo=chunk_repo, document_repo=document_repo,
        embedding_repo=embedding_repo, embedding_provider=embedding_provider, user_id="user-1",
    )

    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None,
        question="The derivative of x^2 is 2x.",
    )

    assert result.user_message.role == "user"
    assert result.assistant_message.role == "assistant"
    assert result.assistant_message.content == "The derivative of x^2 is 2x [1]."
    assert len(result.assistant_message.citations) == 1
    citation = result.assistant_message.citations[0]
    assert citation.document_filename == "calc101.pdf"
    assert citation.chunk_id == child.id
    assert citation.page == 3


async def test_send_message_reuses_existing_conversation_and_condenses_with_history():
    # Turn 1 has no history, so condense_question makes no LLM call — only the
    # answer-generation call happens. Turn 2 has history, so condense_question
    # makes a call too: [turn1_answer, turn2_condensed_question, turn2_answer].
    llm = FakeLLMProvider(
        responses=["The derivative of x^2 is 2x.", "what is the derivative of x^2", "Answer using history."]
    )
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject, document, child = await _seed_document_and_chunks(
        subject_repo=subject_repo, chunk_repo=chunk_repo, document_repo=document_repo,
        embedding_repo=embedding_repo, embedding_provider=embedding_provider, user_id="user-1",
    )

    first = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None, question="Tell me about derivatives"
    )
    second = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=first.conversation.id,
        question="what's its derivative",
    )

    assert second.conversation.id == first.conversation.id
    assert second.assistant_message.content == "Answer using history."
    # condense_question's LLM call (the 2nd overall call) should have seen turn 1's messages.
    condense_call = llm.calls[1]
    assert "Tell me about derivatives" in condense_call["prompt"]
    assert "The derivative of x^2 is 2x." in condense_call["prompt"]


async def test_send_message_cites_each_document_only_once():
    """Two different chunks from the same document both matching shouldn't
    produce two citations for that document — see _generate_answer's
    seen_document_ids dedup."""
    llm = FakeLLMProvider(response="The derivative of x^2 is 2x [1][2].")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm, final_context_chunks=5
    )
    subject = await subject_repo.create(user_id="user-1", name="Calculus", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="calc101.pdf",
        storage_path="x", file_type="pdf",
    )
    drafts = [
        ChunkDraft(
            content="Derivatives measure the rate of change of a function.", chunk_type="parent",
            parent_index=None, page=3, section_title="Ch1", chapter=None, token_count=8,
        ),
        ChunkDraft(
            content="The derivative of x^2 is 2x.", chunk_type="child", parent_index=0, page=3,
            section_title="Ch1", chapter=None, token_count=7,
        ),
        ChunkDraft(
            content="The derivative of x^3 is 3x^2.", chunk_type="child", parent_index=0, page=4,
            section_title="Ch1", chapter=None, token_count=7,
        ),
    ]
    chunks = await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    children = [c for c in chunks if c.chunk_type == "child"]
    vectors = await embedding_provider.embed_documents([c.content for c in children])
    await embedding_repo.bulk_create(
        chunk_ids=[c.id for c in children], vectors=vectors, model_name=embedding_provider.model_name
    )

    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None,
        question="How do you differentiate polynomials?",
    )

    assert len(result.assistant_message.citations) == 1
    assert result.assistant_message.citations[0].document_filename == "calc101.pdf"


async def test_send_message_no_matching_chunks_returns_fallback_with_no_citations():
    llm = FakeLLMProvider(response="should not be called for the answer")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject = await subject_repo.create(user_id="user-1", name="Empty Subject", description=None, color=None, icon=None)

    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None, question="anything"
    )

    assert result.assistant_message.citations == []
    assert "couldn't find" in result.assistant_message.content


async def test_send_message_scoped_to_document_id_ignores_other_documents():
    llm = FakeLLMProvider(response="Answer scoped to one document [1].")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject, document, child = await _seed_document_and_chunks(
        subject_repo=subject_repo, chunk_repo=chunk_repo, document_repo=document_repo,
        embedding_repo=embedding_repo, embedding_provider=embedding_provider, user_id="user-1",
    )
    # A second document in the same subject with the exact same content —
    # if document_id scoping weren't applied, its chunk would also match.
    other_document = await document_repo.create(
        document_id="doc-2", subject_id=subject.id, original_filename="other.pdf",
        storage_path="y", file_type="pdf",
    )
    other_drafts = [
        ChunkDraft(
            content="Derivatives measure the rate of change of a function.", chunk_type="parent",
            parent_index=None, page=1, section_title=None, chapter=None, token_count=8,
        ),
        ChunkDraft(
            content="The derivative of x^2 is 2x.", chunk_type="child", parent_index=0, page=1,
            section_title=None, chapter=None, token_count=7,
        ),
    ]
    other_chunks = await chunk_repo.bulk_create(document_id=other_document.id, subject_id=subject.id, drafts=other_drafts)
    other_child = next(c for c in other_chunks if c.chunk_type == "child")
    other_vector = await embedding_provider.embed_documents([other_child.content])
    await embedding_repo.bulk_create(
        chunk_ids=[other_child.id], vectors=other_vector, model_name=embedding_provider.model_name
    )

    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None,
        question="The derivative of x^2 is 2x.", document_id=document.id,
    )

    assert len(result.assistant_message.citations) == 1
    assert result.assistant_message.citations[0].chunk_id == child.id


async def test_send_message_raises_when_subject_not_owned():
    llm = FakeLLMProvider(response="x")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject = await subject_repo.create(user_id="user-1", name="Calc", description=None, color=None, icon=None)

    with pytest.raises(SubjectNotFoundError):
        await service.send_message(
            user_id="someone-else", subject_id=subject.id, conversation_id=None, question="q"
        )


async def test_list_messages_raises_when_conversation_not_owned():
    llm = FakeLLMProvider(response="x")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject, document, child = await _seed_document_and_chunks(
        subject_repo=subject_repo, chunk_repo=chunk_repo, document_repo=document_repo,
        embedding_repo=embedding_repo, embedding_provider=embedding_provider, user_id="user-1",
    )
    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None, question="derivative of x^2"
    )

    with pytest.raises(ConversationNotFoundError):
        await service.list_messages(user_id="someone-else", conversation_id=result.conversation.id)


async def test_list_messages_returns_oldest_first():
    llm = FakeLLMProvider(response="answer")
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm
    )
    subject, document, child = await _seed_document_and_chunks(
        subject_repo=subject_repo, chunk_repo=chunk_repo, document_repo=document_repo,
        embedding_repo=embedding_repo, embedding_provider=embedding_provider, user_id="user-1",
    )
    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None, question="derivative of x^2"
    )

    messages = await service.list_messages(user_id="user-1", conversation_id=result.conversation.id)

    assert [m.role for m in messages] == ["user", "assistant"]


async def test_send_message_with_hyde_and_multi_query_and_rerank_enabled():
    # keep_k (final_context_chunks=1) must be smaller than the retrieved pool
    # for rerank() to actually issue an LLM call instead of short-circuiting.
    llm = FakeLLMProvider(
        responses=[
            json.dumps({"hypothetical_answer": "2x", "variations": ["d/dx of x squared"]}),
            json.dumps({"scores": [{"index": 0, "relevance": 0.9}, {"index": 1, "relevance": 0.1}]}),
            "Final answer with rerank.",
        ]
    )
    service, subject_repo, chunk_repo, document_repo, embedding_repo, embedding_provider = await _build_chat_service(
        llm=llm, enable_hyde=True, enable_multi_query=True, enable_rerank=True, final_context_chunks=1,
    )
    subject = await subject_repo.create(user_id="user-1", name="Calculus", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="calc101.pdf",
        storage_path="x", file_type="pdf",
    )
    drafts = [
        ChunkDraft(
            content="Derivatives measure the rate of change of a function.", chunk_type="parent",
            parent_index=None, page=3, section_title="Ch1", chapter=None, token_count=8,
        ),
        ChunkDraft(
            content="The derivative of x^2 is 2x.", chunk_type="child", parent_index=0, page=3,
            section_title="Ch1", chapter=None, token_count=7,
        ),
        ChunkDraft(
            content="The derivative of x^3 is 3x^2.", chunk_type="child", parent_index=0, page=3,
            section_title="Ch1", chapter=None, token_count=7,
        ),
    ]
    chunks = await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    children = [c for c in chunks if c.chunk_type == "child"]
    vectors = await embedding_provider.embed_documents([c.content for c in children])
    await embedding_repo.bulk_create(
        chunk_ids=[c.id for c in children], vectors=vectors, model_name=embedding_provider.model_name
    )

    result = await service.send_message(
        user_id="user-1", subject_id=subject.id, conversation_id=None, question="derivative of x^2"
    )

    assert result.assistant_message.content == "Final answer with rerank."
    assert len(result.assistant_message.citations) == 1
