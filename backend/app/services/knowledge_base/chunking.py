"""Character-based hierarchical chunking: parent chunks keep enough
surrounding context for coherent concept tagging and citations, child chunks
are the smaller units actually embedded and retrieved for RAG precision.

No tokenizer dependency by design — token counts stored alongside chunks are
a ~4-chars-per-token heuristic, good enough for analytics/storage estimates,
not for exact provider billing.
"""
from app.domain.entities.chunk import ChunkDraft
from app.services.knowledge_base.extractors.base import ExtractedSegment

_SEPARATORS = ["\n\n", "\n", ". ", " "]


def chunk_segments(
    segments: list[ExtractedSegment],
    *,
    parent_chars: int = 900,
    child_chars: int = 220,
    overlap_chars: int = 40,
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []

    for segment in segments:
        for parent_text in _split_text(segment.text, parent_chars):
            parent_index = len(drafts)
            drafts.append(
                ChunkDraft(
                    content=parent_text,
                    chunk_type="parent",
                    parent_index=None,
                    page=segment.page,
                    section_title=segment.section_title,
                    chapter=None,
                    token_count=_estimate_tokens(parent_text),
                )
            )

            child_texts = _split_text(parent_text, child_chars, overlap_chars) or [parent_text]
            for child_text in child_texts:
                drafts.append(
                    ChunkDraft(
                        content=child_text,
                        chunk_type="child",
                        parent_index=parent_index,
                        page=segment.page,
                        section_title=segment.section_title,
                        chapter=None,
                        token_count=_estimate_tokens(child_text),
                    )
                )

    return drafts


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_text(text: str, max_chars: int, overlap_chars: int = 0) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    pieces = _recursive_split(text, max_chars, _SEPARATORS)
    if overlap_chars <= 0:
        return pieces
    return _apply_overlap(pieces, overlap_chars)


def _recursive_split(text: str, max_chars: int, separators: list[str]) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    if not separators:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    separator, *remaining_separators = separators
    parts = text.split(separator)
    if len(parts) == 1:
        return _recursive_split(text, max_chars, remaining_separators)

    chunks: list[str] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer}{separator}{part}" if buffer else part
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(part) > max_chars:
            chunks.extend(_recursive_split(part, max_chars, remaining_separators))
            buffer = ""
        else:
            buffer = part
    if buffer:
        chunks.append(buffer)

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _apply_overlap(pieces: list[str], overlap_chars: int) -> list[str]:
    if len(pieces) <= 1:
        return pieces
    result = [pieces[0]]
    for piece in pieces[1:]:
        previous = result[-1]
        carry = previous[-overlap_chars:] if len(previous) > overlap_chars else previous
        result.append(f"{carry} {piece}".strip())
    return result
