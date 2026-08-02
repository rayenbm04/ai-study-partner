from collections.abc import Awaitable, Callable

from app.core.exceptions import UnsupportedFileTypeError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.knowledge_base.extractors.docx import extract_docx
from app.services.knowledge_base.extractors.image import extract_image
from app.services.knowledge_base.extractors.pdf import extract_pdf
from app.services.knowledge_base.extractors.pptx import extract_pptx
from app.services.knowledge_base.extractors.txt import extract_txt
from app.services.knowledge_base.extractors.xls import extract_xls
from app.services.knowledge_base.extractors.xlsx import extract_xlsx
from app.services.llm.base import LLMProvider

# Every extractor takes the raw bytes, the original filename (for error
# messages/mime lookup), and an optional LLMProvider — only the PDF (scanned
# pages), PPTX (embedded images), and standalone-image extractors actually use
# it. All of them are async because the vision-capable ones need to await an
# API call; text-only formats just don't happen to await anything.
Extractor = Callable[[bytes, str, LLMProvider | None], Awaitable[list[ExtractedSegment]]]

_EXTRACTORS: dict[str, Extractor] = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".xlsx": extract_xlsx,
    ".xls": extract_xls,
    ".txt": extract_txt,
    ".md": extract_txt,
    ".png": extract_image,
    ".jpg": extract_image,
    ".jpeg": extract_image,
    ".webp": extract_image,
}

SUPPORTED_EXTENSIONS = frozenset(_EXTRACTORS.keys())


def get_extractor(filename: str) -> Extractor:
    extension = extension_of(filename)
    extractor = _EXTRACTORS.get(extension)
    if extractor is None:
        raise UnsupportedFileTypeError(filename)
    return extractor


def extension_of(filename: str) -> str:
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index != -1 else ""
