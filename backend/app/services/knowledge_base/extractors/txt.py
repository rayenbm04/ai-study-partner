from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment


def extract_txt(content: bytes, filename: str) -> list[ExtractedSegment]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            raise ExtractionError(filename, str(exc)) from exc

    text = text.strip()
    if not text:
        return []
    return [ExtractedSegment(text=text, page=None, section_title=None)]
