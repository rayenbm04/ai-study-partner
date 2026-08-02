"""These build small real files in memory (PDF via reportlab, DOCX/PPTX/XLSX
via their own write APIs) and run the actual extractor against them — not
mocks. If pdfplumber, python-docx, python-pptx, or openpyxl ever change how
they expose text, these fail for real instead of a mock quietly agreeing."""
import io

import pytest
from docx import Document as DocxDocument
from openpyxl import Workbook
from pptx import Presentation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.extractors.docx import extract_docx
from app.services.knowledge_base.extractors.pdf import extract_pdf
from app.services.knowledge_base.extractors.pptx import extract_pptx
from app.services.knowledge_base.extractors.registry import SUPPORTED_EXTENSIONS, extension_of, get_extractor
from app.services.knowledge_base.extractors.txt import extract_txt
from app.services.knowledge_base.extractors.xlsx import extract_xlsx


def _make_pdf(pages: list[str]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    for text in pages:
        c.drawString(72, 700, text)
        c.showPage()
    c.save()
    return buffer.getvalue()


def test_extract_pdf_returns_one_segment_per_page():
    content = _make_pdf(["First page of the course.", "Second page continues here."])
    segments = extract_pdf(content, "notes.pdf")

    assert len(segments) == 2
    assert segments[0].page == 1
    assert "First page" in segments[0].text
    assert segments[1].page == 2
    assert "Second page" in segments[1].text


def test_extract_pdf_skips_blank_pages():
    content = _make_pdf(["Only real content page.", ""])
    segments = extract_pdf(content, "notes.pdf")
    assert len(segments) == 1


def test_extract_pdf_raises_extraction_error_on_garbage_bytes():
    with pytest.raises(ExtractionError):
        extract_pdf(b"this is not a pdf", "broken.pdf")


def _make_docx() -> bytes:
    document = DocxDocument()
    document.add_heading("Chapter 1: Vectors", level=1)
    document.add_paragraph("A vector has magnitude and direction.")
    document.add_heading("Chapter 2: Matrices", level=1)
    document.add_paragraph("A matrix is a rectangular array of numbers.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Term"
    table.rows[0].cells[1].text = "Definition"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_docx_groups_paragraphs_under_headings():
    segments = extract_docx(_make_docx(), "algebra.docx")
    section_titles = [s.section_title for s in segments]
    assert "Chapter 1: Vectors" in section_titles
    assert "Chapter 2: Matrices" in section_titles

    vectors_segment = next(s for s in segments if s.section_title == "Chapter 1: Vectors")
    assert "magnitude and direction" in vectors_segment.text


def test_extract_docx_includes_table_content():
    segments = extract_docx(_make_docx(), "algebra.docx")
    assert any("Term | Definition" in s.text for s in segments)


def test_extract_docx_raises_extraction_error_on_garbage_bytes():
    with pytest.raises(ExtractionError):
        extract_docx(b"not a docx file", "broken.docx")


def _make_pptx() -> bytes:
    presentation = Presentation()
    layout = presentation.slide_layouts[1]  # title + content
    slide = presentation.slides.add_slide(layout)
    slide.shapes.title.text = "Newton's Laws"
    slide.placeholders[1].text = "The first law states that an object at rest stays at rest."
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def test_extract_pptx_captures_title_and_body():
    segments = extract_pptx(_make_pptx(), "physics.pptx")
    assert len(segments) == 1
    assert segments[0].section_title == "Newton's Laws"
    assert "object at rest" in segments[0].text
    assert segments[0].page == 1


def test_extract_pptx_raises_extraction_error_on_garbage_bytes():
    with pytest.raises(ExtractionError):
        extract_pptx(b"not a pptx file", "broken.pptx")


def _make_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Formulas"
    sheet.append(["Name", "Formula"])
    sheet.append(["Area of circle", "pi * r^2"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_extract_xlsx_joins_cells_and_uses_sheet_name_as_section():
    segments = extract_xlsx(_make_xlsx(), "formulas.xlsx")
    assert len(segments) == 1
    assert segments[0].section_title == "Formulas"
    assert "Area of circle | pi * r^2" in segments[0].text


def test_extract_xlsx_raises_extraction_error_on_garbage_bytes():
    with pytest.raises(ExtractionError):
        extract_xlsx(b"not an xlsx file", "broken.xlsx")


def test_extract_txt_decodes_utf8():
    segments = extract_txt("Résumé du cours de physique.".encode("utf-8"), "notes.txt")
    assert len(segments) == 1
    assert "Résumé" in segments[0].text


def test_extract_txt_falls_back_to_latin1():
    content = "Café".encode("latin-1")
    segments = extract_txt(content, "notes.txt")
    assert "Caf" in segments[0].text


def test_extract_txt_empty_file_returns_no_segments():
    assert extract_txt(b"   \n  ", "empty.txt") == []


@pytest.mark.parametrize(
    "filename,expected_extension", [("Notes.PDF", ".pdf"), ("slides.pptx", ".pptx"), ("noextension", "")]
)
def test_extension_of(filename, expected_extension):
    assert extension_of(filename) == expected_extension


def test_get_extractor_returns_callable_for_supported_types():
    for extension in SUPPORTED_EXTENSIONS:
        extractor = get_extractor(f"file{extension}")
        assert callable(extractor)


def test_get_extractor_rejects_unsupported_type():
    from app.core.exceptions import UnsupportedFileTypeError

    with pytest.raises(UnsupportedFileTypeError):
        get_extractor("scan.jpg")
