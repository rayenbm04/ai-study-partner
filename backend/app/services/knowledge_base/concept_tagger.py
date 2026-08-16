"""Builds the per-subject concept graph: matches a chunk of course material
against concepts the subject already has, proposes new concepts when the
chunk is clearly about something not yet represented, and wires up
prerequisite edges the LLM identifies between them.

This is the piece that makes the "knowledge graph" more than a chat log —
everything the progress/planning engines do later (mastery rollup, weak-spot
detection, "you can't tackle derivatives until you're solid on limits")
depends on this graph being populated as documents come in.
"""
import json
import logging

from app.domain.entities.concept import Concept
from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are building a knowledge graph for a student's study subject. Given a chunk "
    "of course material and the list of concepts already known for this subject, decide "
    "which existing concepts this chunk is relevant to, and whether it introduces any new "
    "concept not yet in the list. Respond with strict JSON only, matching this shape: "
    '{"matched": [{"name": "<existing concept name>", "relevance": <0-1 float>}], '
    '"new_concepts": [{"name": "<short concept name>", "description": "<one sentence>", '
    '"prerequisites": ["<existing or newly proposed concept name>"]}]}. '
    "Only propose a new concept if the chunk is clearly about something a student would need to "
    "study and understand, and it's distinct from every existing concept. Never propose a concept "
    "for a document's own structure or layout — e.g. 'Exam Format', 'Metadata Table', 'Academic "
    "Header', 'Question Numbering', 'Cover Page', 'Table of Contents' are NOT concepts, no matter "
    "how prominent they are in the chunk; skip them entirely rather than naming the document "
    "artifact itself. Keep concept names short (2-5 words) and reuse the student's own terminology "
    "from the material where possible. Return {\"matched\": [], \"new_concepts\": []} if the chunk "
    "is header/footer/metadata/formatting boilerplate rather than actual subject-matter content."
)

# Same task as _SYSTEM_PROMPT, batched: tags several chunks in one call
# instead of one call per chunk. Ingestion is the dominant source of LLM
# call volume on large documents (one parent chunk per ~900 chars can mean
# hundreds of chunks for a textbook) — this cuts that call count by roughly
# the batch size.
_BATCH_SYSTEM_PROMPT = (
    "You are building a knowledge graph for a student's study subject. You'll be given several "
    "numbered chunks of course material and the list of concepts already known for this subject. "
    "For EACH chunk, decide which existing concepts it's relevant to, and whether it introduces "
    "any new concept not yet in the list. Respond with strict JSON only, matching this shape: "
    '{"chunks": [{"index": <int, the chunk\'s given number>, '
    '"matched": [{"name": "<existing concept name>", "relevance": <0-1 float>}], '
    '"new_concepts": [{"name": "<short concept name>", "description": "<one sentence>", '
    '"prerequisites": ["<existing or newly proposed concept name>"]}]}, ...]}. '
    "Include exactly one entry per chunk, using its given index. Only propose a new concept if a "
    "chunk is clearly about something a student would need to study and understand, distinct from "
    "every existing concept AND from any new concept you're proposing for another chunk in this "
    "same batch — reuse the same name across chunks instead of proposing near-duplicates. Never "
    "propose a concept for a document's own structure or layout — e.g. 'Exam Format', 'Metadata "
    "Table', 'Academic Header', 'Question Numbering', 'Cover Page', 'Table of Contents' are NOT "
    "concepts, no matter how prominent they are in the chunk; skip them entirely rather than naming "
    "the document artifact itself. Keep concept names short (2-5 words) and reuse the student's own "
    "terminology. Use {\"matched\": [], \"new_concepts\": []} for a chunk that's header/footer/"
    "metadata/formatting boilerplate rather than actual subject-matter content."
)


class ConceptTagger:
    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        concept_repo: ConceptRepository,
        concept_chunk_repo: ConceptChunkRepository,
        relevance_threshold: float,
        max_new_concepts: int,
    ):
        self._llm = llm_provider
        self._concepts = concept_repo
        self._concept_chunks = concept_chunk_repo
        self._relevance_threshold = relevance_threshold
        self._max_new_concepts = max_new_concepts

    async def tag_chunk(self, *, subject_id: str, chunk_id: str, chunk_content: str) -> list[str]:
        """Tags `chunk_id` against the subject's concept graph, creating new
        concepts (and their declared prerequisite edges) as needed. Returns
        the ids of every concept the chunk ended up linked to."""
        existing = await self._concepts.list_by_subject(subject_id)
        existing_by_name = {concept.name: concept for concept in existing}

        response_text = await self._llm.complete(
            system=_SYSTEM_PROMPT,
            prompt=self._build_prompt(existing, chunk_content),
            temperature=0.1,
            response_json=True,
        )
        parsed = self._parse_response(response_text)
        if parsed is None:
            return []

        tagged_concept_ids: list[str] = []

        for match in parsed.get("matched", []) or []:
            name = str(match.get("name", "")).strip()
            try:
                relevance = float(match.get("relevance", 0))
            except (TypeError, ValueError):
                continue
            concept = existing_by_name.get(name)
            if concept is None or relevance < self._relevance_threshold:
                continue
            await self._concept_chunks.link(concept_id=concept.id, chunk_id=chunk_id, relevance=relevance)
            tagged_concept_ids.append(concept.id)

        new_concept_proposals = (parsed.get("new_concepts", []) or [])[: self._max_new_concepts]
        newly_created: dict[str, Concept] = {}
        for proposal in new_concept_proposals:
            name = str(proposal.get("name", "")).strip()
            if not name or name in existing_by_name or name in newly_created:
                continue
            description = proposal.get("description")
            concept = await self._concepts.create(subject_id=subject_id, name=name, description=description)
            newly_created[name] = concept
            await self._concept_chunks.link(concept_id=concept.id, chunk_id=chunk_id, relevance=1.0)
            tagged_concept_ids.append(concept.id)

        all_known = {**existing_by_name, **newly_created}
        for proposal in new_concept_proposals:
            name = str(proposal.get("name", "")).strip()
            concept = newly_created.get(name)
            if concept is None:
                continue
            for prerequisite_name in proposal.get("prerequisites", []) or []:
                prerequisite = all_known.get(str(prerequisite_name).strip())
                if prerequisite is not None:
                    await self._concepts.add_prerequisite(concept_id=concept.id, prerequisite_id=prerequisite.id)

        return tagged_concept_ids

    async def tag_chunks(self, *, subject_id: str, chunks: list[tuple[str, str]]) -> None:
        """Batched sibling of tag_chunk: tags every (chunk_id, content) pair
        in `chunks` against the subject's concept graph using a single LLM
        call instead of one call per chunk. Intended for ingestion, where the
        chunk count can be in the hundreds for a large document.

        No return value (unlike tag_chunk) — ingestion doesn't act on which
        concepts a chunk matched, only that the graph gets populated."""
        if not chunks:
            return

        existing = await self._concepts.list_by_subject(subject_id)
        existing_by_name = {concept.name: concept for concept in existing}

        response_text = await self._llm.complete(
            system=_BATCH_SYSTEM_PROMPT,
            prompt=self._build_batch_prompt(existing, chunks),
            temperature=0.1,
            response_json=True,
        )
        parsed = self._parse_response(response_text)
        entries = (parsed or {}).get("chunks")
        if not isinstance(entries, list):
            if parsed is not None:
                logger.warning("Batched concept tagger response missing a 'chunks' list, skipping batch.")
            return

        # Two passes: first link matches and create every new concept
        # (deduped by name across the whole batch, not just within one
        # chunk's proposals — two chunks in the same batch can legitimately
        # both introduce the same concept), then resolve prerequisite edges
        # once every concept in the batch actually exists.
        newly_created: dict[str, Concept] = {}
        proposals_by_index: dict[int, list[dict]] = {}

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                index = int(entry.get("index"))
            except (TypeError, ValueError):
                continue
            if not (0 <= index < len(chunks)):
                continue
            chunk_id, _content = chunks[index]

            for match in entry.get("matched", []) or []:
                name = str(match.get("name", "")).strip()
                try:
                    relevance = float(match.get("relevance", 0))
                except (TypeError, ValueError):
                    continue
                concept = existing_by_name.get(name)
                if concept is None or relevance < self._relevance_threshold:
                    continue
                await self._concept_chunks.link(concept_id=concept.id, chunk_id=chunk_id, relevance=relevance)

            proposals = (entry.get("new_concepts", []) or [])[: self._max_new_concepts]
            proposals_by_index[index] = proposals
            for proposal in proposals:
                name = str(proposal.get("name", "")).strip()
                if not name or name in existing_by_name or name in newly_created:
                    continue
                description = proposal.get("description")
                newly_created[name] = await self._concepts.create(
                    subject_id=subject_id, name=name, description=description
                )

        all_known = {**existing_by_name, **newly_created}
        for index, proposals in proposals_by_index.items():
            chunk_id, _content = chunks[index]
            for proposal in proposals:
                name = str(proposal.get("name", "")).strip()
                concept = all_known.get(name)
                if concept is None:
                    continue
                await self._concept_chunks.link(concept_id=concept.id, chunk_id=chunk_id, relevance=1.0)
                for prerequisite_name in proposal.get("prerequisites", []) or []:
                    prerequisite = all_known.get(str(prerequisite_name).strip())
                    if prerequisite is not None and prerequisite.id != concept.id:
                        await self._concepts.add_prerequisite(concept_id=concept.id, prerequisite_id=prerequisite.id)

    def _build_batch_prompt(self, existing: list[Concept], chunks: list[tuple[str, str]]) -> str:
        concept_list = "\n".join(f"- {concept.name}" for concept in existing) or "(none yet)"
        chunk_blocks = "\n\n".join(
            f'Chunk {i}:\n"""\n{content}\n"""' for i, (_chunk_id, content) in enumerate(chunks)
        )
        return f"Existing concepts for this subject:\n{concept_list}\n\nCourse material chunks:\n{chunk_blocks}"

    def _build_prompt(self, existing: list[Concept], chunk_content: str) -> str:
        concept_list = "\n".join(f"- {concept.name}" for concept in existing) or "(none yet)"
        return f'Existing concepts for this subject:\n{concept_list}\n\nCourse material chunk:\n"""\n{chunk_content}\n"""'

    def _parse_response(self, response_text: str) -> dict | None:
        try:
            parsed = json.loads(response_text)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Concept tagger got a non-JSON response, skipping chunk: %r", response_text[:200])
            return None
        if not isinstance(parsed, dict):
            logger.warning("Concept tagger got a JSON response that wasn't an object, skipping chunk.")
            return None
        return parsed
