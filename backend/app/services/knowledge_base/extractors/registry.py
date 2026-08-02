from collections.abc import Callable

from app.core.exceptions import UnsupportedFileTypeError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.knowledge_base.extractors.docx import extract_docx
from app.services.knowledge_base.extractors.pdf import extract_pdf
from app.services.knowledge_base.extractors.pptx import extract_pptx
from app.services.knowledge_base.extractors.txt import extract_txt
from app.services.knowledge_base.extractors.xlsx import extract_xlsx

Extractor = Callable[[bytes, str], list[ExtractedSegment]]

# Standalone images and scanned-only PDFs aren't supported yet — that needs a
# vision LLM call per page and deserves its own tested increment rather than
# a half-working stub here. Everything below extracts real embedded text.
_EXTRACTORS: dict[str, Extractor] = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".xlsx": extract_xlsx,
    ".txt": extract_txt,
    ".md": extract_txt,
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
