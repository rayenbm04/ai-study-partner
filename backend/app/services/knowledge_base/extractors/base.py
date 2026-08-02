from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedSegment:
    """One coherent unit of extracted text — a PDF page, a slide, a sheet, a
    paragraph run between two headings — before chunking splits it further."""

    text: str
    page: int | None
    section_title: str | None
