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
    "Only propose a new concept if the chunk is clearly about something distinct from every "
    "existing concept. Keep concept names short (2-5 words) and reuse the student's own "
    "terminology from the material where possible. Return {\"matched\": [], \"new_concepts\": []} "
    "if the chunk doesn't correspond to any teachable concept (e.g. a cover page)."
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
