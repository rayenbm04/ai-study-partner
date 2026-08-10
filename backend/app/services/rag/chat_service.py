"""Orchestrates one chat turn end to end: condense the question against
history -> expand it into extra search queries (HyDE + multi-query) ->
retrieve candidate chunks -> rerank -> assemble a citation-annotated answer ->
persist both the user's message and the assistant's reply.

This is the only place these pieces get wired together; query_rewrite.py,
retriever.py and rerank.py are all independently unit-testable against fakes,
and this module's own tests use fakes for everything (repos + LLM +
embedder) so they run with no network and no DB.
"""
import logging
from dataclasses import dataclass

from app.core.exceptions import ConversationNotFoundError
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Citation, Message
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.domain.repositories.message_repository import MessageRepository
from app.services.embeddings.base import EmbeddingProvider
from app.services.llm.base import LLMProvider
from app.services.rag.query_rewrite import condense_question, expand_query
from app.services.rag.rerank import rerank
from app.services.rag.retriever import RetrievedChunk, VectorRetriever
from app.services.subject_service import SubjectService

logger = logging.getLogger(__name__)

_ANSWER_SYSTEM_PROMPT = (
    "You are a study coach helping a student understand their course material. Answer the "
    "student's question using ONLY the numbered excerpts below — if the excerpts don't contain "
    "the answer, say so plainly rather than guessing from general knowledge. Reference excerpts "
    "inline using their number in square brackets, e.g. [1], right after the claim they support. "
    "Be clear and pedagogical: explain the reasoning, not just the conclusion. Keep the tone "
    "encouraging but don't pad the answer with filler."
)


@dataclass(frozen=True, slots=True)
class ChatTurnResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message


class ChatService:
    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        chunk_repo: ChunkRepository,
        document_repo: DocumentRepository,
        embedding_repo: EmbeddingRepository,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        subject_service: SubjectService,
        enable_hyde: bool,
        enable_multi_query: bool,
        enable_rerank: bool,
        multi_query_count: int,
        retrieval_top_k: int,
        final_context_chunks: int,
        history_messages: int,
    ):
        self._conversations = conversation_repo
        self._messages = message_repo
        self._chunks = chunk_repo
        self._documents = document_repo
        self._llm = llm_provider
        self._subjects = subject_service
        self._retriever = VectorRetriever(
            chunk_repo=chunk_repo,
            embedding_repo=embedding_repo,
            embedding_provider=embedding_provider,
            top_k_per_query=retrieval_top_k,
        )
        self._enable_hyde = enable_hyde
        self._enable_multi_query = enable_multi_query
        self._enable_rerank = enable_rerank
        self._multi_query_count = multi_query_count
        self._final_context_chunks = final_context_chunks
        self._history_messages = history_messages

    async def send_message(
        self,
        *,
        user_id: str,
        subject_id: str,
        conversation_id: str | None,
        question: str,
        document_id: str | None = None,
    ) -> ChatTurnResult:
        """`document_id`, when given, scopes retrieval to that one document —
        used when a student opens the coach from a specific upload rather
        than the subject as a whole."""
        await self._subjects.get_owned(user_id, subject_id)  # 404s if this user doesn't own the subject
        conversation = await self._get_or_create_conversation(
            user_id=user_id, subject_id=subject_id, conversation_id=conversation_id, question=question
        )

        history = await self._messages.list_by_conversation(conversation.id)
        recent_history = history[-self._history_messages :] if self._history_messages else []

        standalone_question = await condense_question(
            llm_provider=self._llm, question=question, history=recent_history
        )
        expansion = await expand_query(
            llm_provider=self._llm,
            question=standalone_question,
            enable_hyde=self._enable_hyde,
            enable_multi_query=self._enable_multi_query,
            variation_count=self._multi_query_count,
        )

        queries = [standalone_question]
        if expansion.hypothetical_answer:
            queries.append(expansion.hypothetical_answer)
        queries.extend(expansion.variations)

        # Retrieve a larger pool than we ultimately keep, so reranking has
        # something meaningful to choose between rather than just re-sorting
        # the same handful of results.
        pool_size = self._final_context_chunks * 2 if self._enable_rerank else self._final_context_chunks
        candidates = await self._retriever.retrieve(
            subject_id=subject_id, queries=queries, final_k=pool_size, document_id=document_id
        )

        if self._enable_rerank and candidates:
            candidates = await rerank(
                llm_provider=self._llm,
                question=standalone_question,
                candidates=candidates,
                keep_k=self._final_context_chunks,
            )
        else:
            candidates = candidates[: self._final_context_chunks]

        answer_text, citations = await self._generate_answer(
            question=standalone_question, candidates=candidates, document_id=document_id
        )

        user_message = await self._messages.create(
            conversation_id=conversation.id, role="user", content=question, citations=[]
        )
        assistant_message = await self._messages.create(
            conversation_id=conversation.id, role="assistant", content=answer_text, citations=citations
        )

        return ChatTurnResult(
            conversation=conversation, user_message=user_message, assistant_message=assistant_message
        )

    async def list_conversations(self, *, user_id: str, subject_id: str) -> list[Conversation]:
        await self._subjects.get_owned(user_id, subject_id)
        return await self._conversations.list_by_subject(user_id, subject_id)

    async def list_messages(self, *, user_id: str, conversation_id: str) -> list[Message]:
        conversation = await self._get_owned_conversation(user_id, conversation_id)
        return await self._messages.list_by_conversation(conversation.id)

    async def _get_owned_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def _get_or_create_conversation(
        self, *, user_id: str, subject_id: str, conversation_id: str | None, question: str
    ) -> Conversation:
        if conversation_id is not None:
            conversation = await self._conversations.get_by_id(conversation_id)
            if conversation is not None and conversation.user_id == user_id and conversation.subject_id == subject_id:
                return conversation
            logger.warning("conversation_id %s not found or not owned, starting a new conversation", conversation_id)

        title = question.strip()[:80] or None
        return await self._conversations.create(user_id=user_id, subject_id=subject_id, title=title)

    async def _generate_answer(
        self, *, question: str, candidates: list[RetrievedChunk], document_id: str | None = None
    ) -> tuple[str, list[Citation]]:
        if not candidates:
            scope = "this document" if document_id else "your uploaded material for this subject"
            return (
                f"I couldn't find anything in {scope} that addresses that question. Try "
                "rephrasing, or upload material that covers it.",
                [],
            )

        document_ids = {c.chunk.document_id for c in candidates}
        documents_by_id = {}
        for document_id in document_ids:
            document = await self._documents.get_by_id(document_id)
            if document is not None:
                documents_by_id[document_id] = document

        excerpts = "\n\n".join(
            f"[{i + 1}] {c.context_text}" for i, c in enumerate(candidates)
        )
        prompt = f"Excerpts:\n{excerpts}\n\nStudent's question: {question}"

        answer_text = await self._llm.complete(
            system=_ANSWER_SYSTEM_PROMPT, prompt=prompt, temperature=0.3, max_output_tokens=1500
        )

        citations = [
            Citation(
                document_id=c.chunk.document_id,
                document_filename=documents_by_id[c.chunk.document_id].original_filename
                if c.chunk.document_id in documents_by_id
                else "unknown",
                chunk_id=c.chunk.id,
                page=c.chunk.page,
                section_title=c.chunk.section_title,
            )
            for c in candidates
        ]
        return answer_text, citations
