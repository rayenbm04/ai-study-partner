from app.services.knowledge_base.chunking import chunk_segments
from app.services.knowledge_base.extractors.base import ExtractedSegment


def test_short_segment_yields_one_parent_and_one_child():
    segments = [ExtractedSegment(text="A short paragraph about limits.", page=1, section_title="Intro")]
    drafts = chunk_segments(segments, parent_chars=900, child_chars=220, overlap_chars=40)

    parents = [d for d in drafts if d.chunk_type == "parent"]
    children = [d for d in drafts if d.chunk_type == "child"]
    assert len(parents) == 1
    assert len(children) == 1
    assert parents[0].content == "A short paragraph about limits."
    assert children[0].parent_index == drafts.index(parents[0])
    assert parents[0].page == 1
    assert parents[0].section_title == "Intro"


def test_long_segment_splits_into_multiple_parents():
    long_text = "\n\n".join(f"Paragraph number {i} with some real sentences in it. " * 5 for i in range(20))
    segments = [ExtractedSegment(text=long_text, page=3, section_title="Chapter 2")]
    drafts = chunk_segments(segments, parent_chars=300, child_chars=100, overlap_chars=20)

    parents = [d for d in drafts if d.chunk_type == "parent"]
    assert len(parents) > 1
    for parent in parents:
        assert len(parent.content) <= 320  # a little slack for the recursive splitter's separators
        assert parent.page == 3
        assert parent.section_title == "Chapter 2"


def test_every_child_references_a_valid_parent_index():
    long_text = "Sentence one. " * 200
    segments = [ExtractedSegment(text=long_text, page=None, section_title=None)]
    drafts = chunk_segments(segments, parent_chars=300, child_chars=80, overlap_chars=15)

    parent_indices = {i for i, d in enumerate(drafts) if d.chunk_type == "parent"}
    for draft in drafts:
        if draft.chunk_type == "child":
            assert draft.parent_index in parent_indices


def test_overlap_carries_tail_of_previous_child_into_next():
    long_text = "word " * 300
    segments = [ExtractedSegment(text=long_text, page=None, section_title=None)]
    drafts = chunk_segments(segments, parent_chars=5000, child_chars=100, overlap_chars=30)

    children = [d for d in drafts if d.chunk_type == "child"]
    assert len(children) > 1
    # the tail of the first child should reappear at the start of the second
    tail = children[0].content[-20:]
    assert tail in children[1].content


def test_empty_segments_produce_no_drafts():
    assert chunk_segments([]) == []
    assert chunk_segments([ExtractedSegment(text="   ", page=1, section_title=None)]) == []


def test_token_count_is_a_positive_heuristic():
    segments = [ExtractedSegment(text="Some reasonably long piece of text to estimate tokens for.", page=None, section_title=None)]
    drafts = chunk_segments(segments)
    assert all(d.token_count >= 1 for d in drafts)
