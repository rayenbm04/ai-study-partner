import io

from pptx import Presentation

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment


def extract_pptx(content: bytes, filename: str) -> list[ExtractedSegment]:
    try:
        presentation = Presentation(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(filename, str(exc)) from exc

    segments: list[ExtractedSegment] = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        title_shape = slide.shapes.title
        title_shape_id = title_shape.shape_id if title_shape is not None else None

        title: str | None = None
        body_parts: list[str] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue
            if title_shape_id is not None and shape.shape_id == title_shape_id:
                title = text
            else:
                body_parts.append(text)

        body = "\n".join(body_parts).strip()
        combined = f"{title}\n{body}".strip() if title else body
        if combined:
            segments.append(ExtractedSegment(text=combined, page=slide_number, section_title=title))

    return segments
