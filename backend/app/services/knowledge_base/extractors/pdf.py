import io
import re

import pdfplumber

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.llm.base import LLMProvider

# pdfplumber occasionally emits unresolved-ligature placeholders instead of
# the actual character, and mis-maps accented Latin characters through a
# MacRoman/custom font encoding — most visible in French course PDFs, which
# is most of what this app ingests. Ported from the original rag-backend's
# _fix_pdf_text, same mapping.
_CID_MAP: dict[str, str] = {
    "(cid:11)": "fi", "(cid:12)": "fl", "(cid:13)": "ff",
    "(cid:14)": "ffi", "(cid:15)": "ffl",
    "(cid:28)": "fi", "(cid:29)": "fl", "(cid:30)": "ff",
    "(cid:31)": "ffi", "(cid:32)": "ffl",
    "(cid:1)": "!", "(cid:2)": '"', "(cid:3)": "#",
}
_ENCODING_FIX: dict[str, str] = {
    "Ø": "é", "ø": "è", "Æ": "à", "æ": "â", "Å": "ê", "å": "ë",
    "Ã": "î", "ã": "ï", "Œ": "ô", "œ": "ù", "Ç": "ç", "ß": "û", "†": "°",
}
_CID_PATTERN = re.compile(r"\(cid:\d+\)")

# Below this many characters of real text, a page is treated as scanned/image-only.
_MIN_TEXT_CHARS_BEFORE_VISION_FALLBACK = 50

_VISION_PROMPT = (
    "Transcribe all text on this page verbatim, including any tables (as markdown "
    "tables) and figure captions. This is a page from a student's course material. "
    "Output only the transcribed content, no commentary."
)


def _fix_pdf_text(text: str) -> str:
    for cid, replacement in _CID_MAP.items():
        text = text.replace(cid, replacement)
    text = _CID_PATTERN.sub("", text)
    for wrong, correct in _ENCODING_FIX.items():
        text = text.replace(wrong, correct)
    return text


async def extract_pdf(
    content: bytes, filename: str, llm_provider: LLMProvider | None = None
) -> list[ExtractedSegment]:
    segments: list[ExtractedSegment] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            total_pages = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                text = _fix_pdf_text(page.extract_text() or "").strip()

                if len(text) < _MIN_TEXT_CHARS_BEFORE_VISION_FALLBACK and llm_provider is not None:
                    # Scanned/image-only page — no meaningful text layer, so
                    # ask the vision model to transcribe it instead of
                    # silently dropping the page's content.
                    vision_text = await _vision_fallback(page, page_number, total_pages, llm_provider)
                    text = vision_text or text

                if text:
                    segments.append(ExtractedSegment(text=text, page=page_number, section_title=None))
    except Exception as exc:  # pdfplumber/pdfminer raise a variety of exception types
        raise ExtractionError(filename, str(exc)) from exc
    return segments


async def _vision_fallback(page, page_number: int, total_pages: int, llm_provider: LLMProvider) -> str:
    try:
        image = page.to_image(resolution=150).original
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        prompt = f"{_VISION_PROMPT}\n\n(Page {page_number} of {total_pages}.)"
        response = await llm_provider.complete_vision(
            image_bytes=buffer.getvalue(), mime_type="image/png", prompt=prompt
        )
        return response.strip()
    except Exception:
        # A vision-call failure shouldn't fail the whole document — the page
        # just falls back to whatever (possibly empty) text pdfplumber found.
        return ""
