import json

from app.services.knowledge_base.concept_tagger import ConceptTagger
from tests.unit.fakes import FakeConceptChunkRepository, FakeConceptRepository, FakeLLMProvider


async def test_creates_new_concept_and_links_chunk():
    llm = FakeLLMProvider(
        response=json.dumps(
            {"matched": [], "new_concepts": [{"name": "Derivatives", "description": "Rate of change", "prerequisites": []}]}
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    tagged_ids = await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="d/dx of x^2 is 2x")

    concepts = await concept_repo.list_by_subject("subj-1")
    assert len(concepts) == 1
    assert concepts[0].name == "Derivatives"
    assert tagged_ids == [concepts[0].id]
    assert concept_chunk_repo.links == [(concepts[0].id, "chunk-1", 1.0)]


async def test_matches_existing_concept_above_threshold():
    llm = FakeLLMProvider(response=json.dumps({"matched": [{"name": "Limits", "relevance": 0.8}], "new_concepts": []}))
    concept_repo = FakeConceptRepository()
    existing = await concept_repo.create(subject_id="subj-1", name="Limits", description=None)
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    tagged_ids = await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="lim x->0 sin(x)/x")

    assert tagged_ids == [existing.id]
    assert concept_chunk_repo.links == [(existing.id, "chunk-1", 0.8)]


async def test_match_below_threshold_is_dropped():
    llm = FakeLLMProvider(response=json.dumps({"matched": [{"name": "Limits", "relevance": 0.2}], "new_concepts": []}))
    concept_repo = FakeConceptRepository()
    await concept_repo.create(subject_id="subj-1", name="Limits", description=None)
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    tagged_ids = await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="irrelevant")

    assert tagged_ids == []
    assert concept_chunk_repo.links == []


async def test_prerequisite_edge_created_between_two_new_concepts():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "matched": [],
                "new_concepts": [
                    {"name": "Limits", "description": "Basics", "prerequisites": []},
                    {"name": "Derivatives", "description": "Builds on limits", "prerequisites": ["Limits"]},
                ],
            }
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="...")

    concepts = {c.name: c for c in await concept_repo.list_by_subject("subj-1")}
    assert concept_repo.prerequisites == [(concepts["Derivatives"].id, concepts["Limits"].id)]


async def test_hallucinated_prerequisite_name_is_silently_dropped():
    llm = FakeLLMProvider(
        response=json.dumps(
            {"matched": [], "new_concepts": [{"name": "Integrals", "description": "...", "prerequisites": ["Nonexistent Concept"]}]}
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="...")

    assert concept_repo.prerequisites == []  # no crash, no edge to nothing


async def test_new_concepts_capped_at_max_new_concepts():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "matched": [],
                "new_concepts": [
                    {"name": f"Concept {i}", "description": "...", "prerequisites": []} for i in range(5)
                ],
            }
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=2,
    )

    tagged_ids = await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="...")

    assert len(tagged_ids) == 2


async def test_non_json_response_is_handled_gracefully():
    llm = FakeLLMProvider(response="I cannot help with that.")
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    tagged_ids = await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="...")

    assert tagged_ids == []


async def test_tag_chunks_batches_multiple_chunks_into_one_call():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "chunks": [
                    {"index": 0, "matched": [], "new_concepts": [
                        {"name": "Derivatives", "description": "Rate of change", "prerequisites": []}
                    ]},
                    {"index": 1, "matched": [], "new_concepts": [
                        {"name": "Integrals", "description": "Area under a curve", "prerequisites": ["Derivatives"]}
                    ]},
                ]
            }
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunks(
        subject_id="subj-1",
        chunks=[("chunk-1", "d/dx of x^2 is 2x"), ("chunk-2", "integral of 2x is x^2")],
    )

    assert len(llm.calls) == 1  # one call tagged both chunks
    concepts = {c.name: c for c in await concept_repo.list_by_subject("subj-1")}
    assert set(concepts) == {"Derivatives", "Integrals"}
    assert (concepts["Derivatives"].id, "chunk-1", 1.0) in concept_chunk_repo.links
    assert (concepts["Integrals"].id, "chunk-2", 1.0) in concept_chunk_repo.links
    assert concept_repo.prerequisites == [(concepts["Integrals"].id, concepts["Derivatives"].id)]


async def test_tag_chunks_dedupes_same_new_concept_proposed_by_two_chunks():
    llm = FakeLLMProvider(
        response=json.dumps(
            {
                "chunks": [
                    {"index": 0, "matched": [], "new_concepts": [
                        {"name": "Newton's First Law", "description": "Inertia", "prerequisites": []}
                    ]},
                    {"index": 1, "matched": [], "new_concepts": [
                        {"name": "Newton's First Law", "description": "Inertia", "prerequisites": []}
                    ]},
                ]
            }
        )
    )
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunks(subject_id="subj-1", chunks=[("chunk-1", "..."), ("chunk-2", "...")])

    concepts = await concept_repo.list_by_subject("subj-1")
    assert len(concepts) == 1  # created once, not twice
    assert {chunk_id for _cid, chunk_id, _rel in concept_chunk_repo.links} == {"chunk-1", "chunk-2"}


async def test_tag_chunks_empty_list_makes_no_llm_call():
    llm = FakeLLMProvider(response="{}")
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=FakeConceptRepository(), concept_chunk_repo=FakeConceptChunkRepository(),
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunks(subject_id="subj-1", chunks=[])

    assert llm.calls == []


async def test_tag_chunks_matches_existing_concept_for_specific_chunk():
    concept_repo = FakeConceptRepository()
    existing = await concept_repo.create(subject_id="subj-1", name="Limits", description=None)
    llm = FakeLLMProvider(
        response=json.dumps(
            {"chunks": [{"index": 0, "matched": [{"name": "Limits", "relevance": 0.9}], "new_concepts": []}]}
        )
    )
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunks(subject_id="subj-1", chunks=[("chunk-1", "lim x->0 sin(x)/x")])

    assert concept_chunk_repo.links == [(existing.id, "chunk-1", 0.9)]


async def test_existing_concepts_are_included_in_prompt():
    concept_repo = FakeConceptRepository()
    await concept_repo.create(subject_id="subj-1", name="Limits", description=None)
    llm = FakeLLMProvider(response=json.dumps({"matched": [], "new_concepts": []}))
    concept_chunk_repo = FakeConceptChunkRepository()
    tagger = ConceptTagger(
        llm_provider=llm, concept_repo=concept_repo, concept_chunk_repo=concept_chunk_repo,
        relevance_threshold=0.5, max_new_concepts=3,
    )

    await tagger.tag_chunk(subject_id="subj-1", chunk_id="chunk-1", chunk_content="some text")

    assert "Limits" in llm.calls[0]["prompt"]
    assert llm.calls[0]["response_json"] is True
