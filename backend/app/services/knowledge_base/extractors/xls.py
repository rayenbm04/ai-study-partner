import xlrd

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.base import ExtractedSegment
from app.services.llm.base import LLMProvider


async def extract_xls(
    content: bytes, filename: str, llm_provider: LLMProvider | None = None
) -> list[ExtractedSegment]:
    """Legacy .xls (pre-2007 binary format) — openpyxl can't read these, xlrd
    dropped .xlsx support years ago but still reads the old binary format."""
    try:
        workbook = xlrd.open_workbook(file_contents=content)
    except Exception as exc:
        raise ExtractionError(filename, str(exc)) from exc

    segments: list[ExtractedSegment] = []
    for sheet_index in range(workbook.nsheets):
        sheet = workbook.sheet_by_index(sheet_index)
        lines: list[str] = []
        for row_index in range(sheet.nrows):
            cells = [str(cell.value) for cell in sheet.row(row_index) if str(cell.value).strip()]
            if cells:
                lines.append(" | ".join(cells))
        text = "\n".join(lines).strip()
        if text:
            segments.append(ExtractedSegment(text=text, page=sheet_index + 1, section_title=sheet.name))
    return segments
