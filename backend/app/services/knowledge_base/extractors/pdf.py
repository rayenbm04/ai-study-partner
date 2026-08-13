import asyncio
import io
import logging
import re

import pdfplumber

from app.core.config import settings
from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

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

# A page that already has plenty of extracted text can still contain a
# diagram/chart/photo worth describing — an embedded image has to cover at
# least this fraction of the page area to count (filters out bullet icons,
# logos, and other decorative slivers that aren't worth a vision call).
_MIN_IMAGE_AREA_RATIO = 0.03

_VISION_PROMPT = (
    "Transcribe all text on this page verbatim, including any tables (as markdown "
    "tables) and figure captions. This is a page from a student's course material. "
    "Output only the transcribed content, no commentary."
)

_IMAGE_DESCRIPTION_PROMPT = (
    "This page from a student's course material already has its text captured separately — don't "
    "transcribe it again. Describe only the diagrams, charts, figures, or photographs on this page: "
    "what they show, and any labels or values visible in them, in 2-4 sentences. If the page has no "
    "meaningful diagram or image (only decorative elements, logos, or icons), respond with exactly "
    "the single word NONE."
)


def _has_significant_image(page) -> bool:
    page_area = (page.width or 0) * (page.height or 0)
    if page_area <= 0:
        return False
    for image in page.images:
        width = image.get("x1", 0) - image.get("x0", 0)
        height = image.get("bottom", 0) - image.get("top", 0)
        if width <= 0 or height <= 0:
            continue
        if (width * height) / page_area >= _MIN_IMAGE_AREA_RATIO:
            return True
    return False


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
            texts: dict[int, str] = {}
            # mode "transcribe": no usable text layer, vision replaces the
            # page's text entirely. mode "describe": text is already fine,
            # but the page also has a diagram/figure worth describing — the
            # description is appended, not a replacement.
            vision_pages: list[tuple[int, object, str]] = []

            for page_number, page in enumerate(pdf.pages, start=1):
                text = _fix_pdf_text(page.extract_text() or "").strip()
                texts[page_number] = text
                if llm_provider is None:
                    continue
                if len(text) < _MIN_TEXT_CHARS_BEFORE_VISION_FALLBACK:
                    # Scanned/image-only page — no meaningful text layer, so
                    # ask the vision model to transcribe it instead of
                    # silently dropping the page's content.
                    vision_pages.append((page_number, page, "transcribe"))
                elif _has_significant_image(page):
                    # Plenty of text, but also a diagram/chart/photo the text
                    # layer doesn't capture — describe it rather than
                    # silently dropping the visual content on a "normal"
                    # digital-text page.
                    vision_pages.append((page_number, page, "describe"))

            if vision_pages:
                # Most documents are normal digital PDFs where this list is
                # empty — a scanned/handwritten document, or one with actual
                # diagrams, is the case this exists for, and it's the one
                # place PDF extraction fans out to more than a couple of LLM
                # calls. Bounded concurrency (LLM_MAX_CONCURRENCY) speeds
                # that up without firing dozens of simultaneous requests.
                semaphore = asyncio.Semaphore(max(1, settings.llm_max_concurrency))

                async def _bounded_vision(page_number: int, page, mode: str) -> tuple[int, str, str]:
                    async with semaphore:
                        if mode == "transcribe":
                            vision_text = await _vision_fallback(page, page_number, total_pages, llm_provider)
                        else:
                            vision_text = await _vision_describe_image(page, page_number, total_pages, llm_provider)
                        return page_number, mode, vision_text

                # Neither helper raises (both catch and log internally,
                # returning "" on failure) — gather() here never sees an
                # exception from an individual page.
                for page_number, mode, vision_text in await asyncio.gather(
                    *(_bounded_vision(pn, p, m) for pn, p, m in vision_pages)
                ):
                    if not vision_text:
                        continue
                    if mode == "transcribe":
                        texts[page_number] = vision_text
                    else:
                        existing = texts.get(page_number, "")
                        texts[page_number] = f"{existing}\n\n[Figure]: {vision_text}".strip()

            for page_number in range(1, total_pages + 1):
                text = texts.get(page_number, "")
                if text:
                    segments.append(ExtractedSegment(text=text, page=page_number, section_title=None))
    except Exception as exc:  # pdfplumber/pdfminer raise a variety of exception types
        raise ExtractionError(filename, str(exc)) from exc
    return segments


def _render_page_png(page) -> bytes:
    image = page.to_image(resolution=150).original
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def _vision_fallback(page, page_number: int, total_pages: int, llm_provider: LLMProvider) -> str:
    try:
        prompt = f"{_VISION_PROMPT}\n\n(Page {page_number} of {total_pages}.)"
        response = await llm_provider.complete_vision(
            image_bytes=_render_page_png(page), mime_type="image/png", prompt=prompt
        )
        return response.strip()
    except Exception:
        # A vision-call failure shouldn't fail the whole document — the page
        # just falls back to whatever (possibly empty) text pdfplumber found.
        # Logged (not silent) because a misconfigured vision model — e.g. a
        # text-only chat model reused for vision — fails this way on *every*
        # page, and used to be invisible until every page's text came up
        # empty and the whole document failed with no clue why.
        logger.warning(
            "Vision fallback failed for page %d/%d — falling back to any text pdfplumber found.",
            page_number, total_pages, exc_info=True,
        )
        return ""


async def _vision_describe_image(page, page_number: int, total_pages: int, llm_provider: LLMProvider) -> str:
    try:
        prompt = f"{_IMAGE_DESCRIPTION_PROMPT}\n\n(Page {page_number} of {total_pages}.)"
        response = await llm_provider.complete_vision(
            image_bytes=_render_page_png(page), mime_type="image/png", prompt=prompt
        )
        description = response.strip()
        if not description or description.strip().upper() == "NONE":
            return ""
        return description
    except Exception:
        # Same reasoning as _vision_fallback: a failed description just
        # means the page's text stands alone, not a failed document.
        logger.warning(
            "Vision image description failed for page %d/%d — page text used as-is.",
            page_number, total_pages, exc_info=True,
        )
        return ""
