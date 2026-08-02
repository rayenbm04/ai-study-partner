import io

import pdfplumber

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment


def extract_pdf(content: bytes, filename: str) -> list[ExtractedSegment]:
    segments: list[ExtractedSegment] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    segments.append(ExtractedSegment(text=text, page=page_number, section_title=None))
    except Exception as exc:  # pdfplumber/pdfminer raise a variety of exception types
        raise ExtractionError(filename, str(exc)) from exc
    return segments
