from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """A chunk not yet persisted — produced by the chunker, consumed by the
    chunk repository, which assigns ids and resolves parent/child linkage.

    `parent_index` is the position of this draft's parent *within the same
    list of drafts the chunker returns* (not a separate parent-only index),
    so parent drafts always come before the children that reference them.
    None for parent chunks themselves."""

    content: str
    chunk_type: str  # "parent" | "child"
    parent_index: int | None
    page: int | None
    section_title: str | None
    chapter: str | None
    token_count: int


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    document_id: str
    subject_id: str
    content: str
    chunk_type: str
    parent_chunk_id: str | None
    page: int | None
    section_title: str | None
    chapter: str | None
    token_count: int
