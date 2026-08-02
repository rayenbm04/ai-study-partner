from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.llm.base import LLMProvider

_MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

_IMAGE_PROMPT = (
    "This image was uploaded as course material by a student. Transcribe any text, "
    "formulas, or diagram labels visible in it verbatim, then briefly describe what "
    "the image shows (a diagram, a graph, a photographed page of notes, a chart, "
    "etc.). This is being used to build a searchable knowledge base of the student's "
    "course material, so completeness matters more than brevity."
)


async def extract_image(
    content: bytes, filename: str, llm_provider: LLMProvider | None = None
) -> list[ExtractedSegment]:
    if llm_provider is None:
        raise ExtractionError(
            filename, "image files require a vision-capable LLM provider to extract; none was configured"
        )

    extension = filename[filename.rfind(".") :].lower() if "." in filename else ""
    mime_type = _MIME_TYPES.get(extension, "image/png")

    try:
        description = await llm_provider.complete_vision(
            image_bytes=content, mime_type=mime_type, prompt=_IMAGE_PROMPT
        )
    except Exception as exc:
        raise ExtractionError(filename, str(exc)) from exc

    description = description.strip()
    if not description:
        return []
    return [ExtractedSegment(text=description, page=None, section_title=None)]
