"""Generates document-scoped study aids: short/detailed/bullet summaries,
a key-concepts glossary, a formula sheet, and a definitions glossary.

Unlike RAG chat (Phase 4), this doesn't need vector retrieval — the "corpus"
for a summary is exactly one document, so the source material is just that
document's parent chunks (already-sized context windows from ingestion)
concatenated in page order, capped at settings.summary_max_source_chars so a
huge document doesn't blow a free-tier context window or turn a summary into
an expensive call. The one place this does lean on retrieval-adjacent
infrastructure is `key_concepts`, which grounds its prompt in the concepts
the ingestion pipeline already tagged to this document (via the concept
graph) rather than asking the LLM to invent concept names from scratch.

Each summary is cached per (document_id, summary_type) — generating is an
explicit, cacheable action, not something recomputed on every read.
"""
import logging

from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    InvalidSummaryTypeError,
    SummaryNotFoundError,
)
from app.domain.entities.concept import Concept
from app.domain.entities.document import Document
from app.domain.entities.summary import SUMMARY_TYPES, Summary
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.summary_repository import SummaryRepository
from app.services.document_service import DocumentService
from app.services.knowledge_base.document_source import build_document_source_text
from app.services.llm.base import LLMProvider
from app.services.llm.language import language_instruction

logger = logging.getLogger(__name__)

_SYSTEM_PROMPTS: dict[str, str] = {
    "short": (
        "Write a short summary (2-4 sentences) capturing the core idea of the document below, for "
        "a student reviewing it quickly before class or an exam. Plain prose, no headers or bullets."
    ),
    "detailed": (
        "Write a detailed, well-organized summary of the document below for a student studying it "
        "in depth — cover every major point and how they connect to each other, not just a list of "
        "topics. Use markdown headers for major sections if the material has natural sections."
    ),
    "bullet": (
        "Summarize the document below as a bulleted list of the main points a student needs to "
        "remember. One bullet per distinct point, using markdown '-' bullets, ordered the way the "
        "material presents them."
    ),
    "key_concepts": (
        "List and briefly explain the key concepts covered in the document below, formatted as "
        "'**Concept Name** — one-sentence explanation', one per line. Ground your answer in the "
        "concept list provided (from this subject's concept graph) where it applies, but you may "
        "also surface concepts from the material that aren't in that list yet."
    ),
    "formula_sheet": (
        "Extract every formula, equation, or key quantitative relationship stated in the document "
        "below into an exam-ready formula sheet. For each: the formula itself and a one-line note on "
        "what it's for and what each symbol means, formatted as '**formula** — explanation'. Write "
        "every formula in LaTeX, wrapped in $$...$$ so it renders as its own block instead of being "
        "crammed into the explanation line. If the document contains no formulas, say so plainly "
        "instead of inventing any."
    ),
    "definitions": (
        "Extract every term the document below explicitly defines, or that a student would need to "
        "know the definition of, as a glossary formatted '**Term** — definition', one per line, in "
        "the order each term first appears. If the document defines no clear terms, say so plainly "
        "instead of inventing any."
    ),
}

_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "short": 400,
    "detailed": 2500,
    "bullet": 800,
    "key_concepts": 1000,
    "formula_sheet": 1200,
    "definitions": 1200,
}


class SummaryService:
    def __init__(
        self,
        *,
        summary_repo: SummaryRepository,
        document_service: DocumentService,
        chunk_repo: ChunkRepository,
        concept_repo: ConceptRepository,
        llm_provider: LLMProvider,
        max_source_chars: int,
    ):
        self._summaries = summary_repo
        self._documents = document_service
        self._chunks = chunk_repo
        self._concepts = concept_repo
        self._llm = llm_provider
        self._max_source_chars = max_source_chars

    async def generate(
        self, *, user_id: str, subject_id: str, document_id: str, summary_type: str, language: str = "en"
    ) -> Summary:
        self._validate_type(summary_type)
        document = await self._documents.get_owned(user_id, document_id)
        if document.subject_id != subject_id:
            # A document that exists and belongs to this user, but under a
            # different subject, is indistinguishable from "not found" here —
            # summaries are generated under the subject in the URL, not
            # wherever the document actually lives.
            raise DocumentNotFoundError(document_id)
        if document.status != "ready":
            raise DocumentNotReadyError(document_id, document.status)

        source_text = await build_document_source_text(self._chunks, document, self._max_source_chars)

        extra_context = ""
        if summary_type == "key_concepts":
            concepts = await self._concepts.list_by_document(document_id)
            extra_context = self._format_concepts(concepts)

        prompt = self._build_prompt(document=document, source_text=source_text, extra_context=extra_context)
        system = f"{_SYSTEM_PROMPTS[summary_type]}\n\n{language_instruction(language)}"
        content = await self._llm.complete(
            system=system,
            prompt=prompt,
            temperature=0.2,
            max_output_tokens=_MAX_OUTPUT_TOKENS[summary_type],
        )

        return await self._summaries.upsert(
            document_id=document_id, subject_id=subject_id, summary_type=summary_type, content=content
        )

    async def get_cached(self, *, user_id: str, document_id: str, summary_type: str) -> Summary:
        self._validate_type(summary_type)
        document = await self._documents.get_owned(user_id, document_id)
        summary = await self._summaries.get_by_document_and_type(document.id, summary_type)
        if summary is None:
            raise SummaryNotFoundError(document.id, summary_type)
        return summary

    async def list_for_document(self, *, user_id: str, document_id: str) -> list[Summary]:
        document = await self._documents.get_owned(user_id, document_id)  # 404s if not owned
        return await self._summaries.list_by_document(document.id)

    def _validate_type(self, summary_type: str) -> None:
        if summary_type not in SUMMARY_TYPES:
            raise InvalidSummaryTypeError(summary_type, SUMMARY_TYPES)

    def _format_concepts(self, concepts: list[Concept]) -> str:
        if not concepts:
            return "(This subject's concept graph has no concepts tagged to this document yet.)"
        lines = "\n".join(f"- {c.name}" + (f": {c.description}" if c.description else "") for c in concepts)
        return f"Concepts already tagged to this document in the subject's concept graph:\n{lines}"

    def _build_prompt(self, *, document: Document, source_text: str, extra_context: str) -> str:
        parts = [f"Document: {document.original_filename}"]
        if extra_context:
            parts.append(extra_context)
        parts.append(f'Source material:\n"""\n{source_text}\n"""')
        return "\n\n".join(parts)
