import io
import json

import pytest

from memory_platform.core.exceptions import DocumentProcessingError
from memory_platform.document_processing import extractors
from memory_platform.domain.enums import DocumentType


def _make_pdf_bytes(text: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, text)
    return bytes(pdf.output())


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pptx_bytes(slide_texts: list[str]) -> bytes:
    from pptx import Presentation

    prs = Presentation()
    layout = prs.slide_layouts[1]
    for text in slide_texts:
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = text
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _make_xlsx_bytes(rows: list[list]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_pdf_real_library():
    raw = _make_pdf_bytes("Hello from a real PDF document")
    result = extractors.extract(DocumentType.PDF, raw)
    assert "Hello" in result.text
    assert result.page_count == 1


def test_extract_docx_real_library():
    raw = _make_docx_bytes(["First paragraph.", "Second paragraph with detail."])
    result = extractors.extract(DocumentType.DOCX, raw)
    assert "First paragraph." in result.text
    assert "Second paragraph" in result.text


def test_extract_pptx_real_library():
    raw = _make_pptx_bytes(["Slide One Title", "Slide Two Title"])
    result = extractors.extract(DocumentType.PPTX, raw)
    assert "Slide One Title" in result.text
    assert result.page_count == 2


def test_extract_xlsx_real_library():
    raw = _make_xlsx_bytes([["Name", "Score"], ["Alice", 92], ["Bob", 87]])
    result = extractors.extract(DocumentType.XLSX, raw)
    assert "Alice" in result.text
    assert "92" in result.text
    assert result.extra_metadata["sheet_count"] == 1


def test_extract_csv():
    raw = b"name,score\nAlice,92\nBob,87"
    result = extractors.extract(DocumentType.CSV, raw)
    assert "Alice" in result.text
    assert result.extra_metadata["row_count"] == 3


def test_extract_json():
    raw = json.dumps({"key": "value", "nested": {"a": 1}}).encode()
    result = extractors.extract(DocumentType.JSON, raw)
    assert '"key": "value"' in result.text


def test_extract_html_strips_tags():
    raw = b"<html><head><style>body{color:red}</style></head><body><h1>Title</h1><p>Some <b>bold</b> text.</p></body></html>"
    result = extractors.extract(DocumentType.HTML, raw)
    assert "Title" in result.text
    assert "bold" in result.text
    assert "<" not in result.text
    assert "color:red" not in result.text


def test_extract_markdown_and_text():
    raw = b"# Heading\n\nSome *markdown* content."
    result = extractors.extract(DocumentType.MARKDOWN, raw)
    assert "# Heading" in result.text


def test_extract_image_without_transcription_provider_raises():
    with pytest.raises(DocumentProcessingError):
        extractors.extract(DocumentType.IMAGE, b"fake-image-bytes")


def test_extract_audio_with_custom_transcription_provider():
    class FakeTranscriber:
        def transcribe(self, raw_bytes, *, document_type):
            return "this is the transcript"

    result = extractors.extract(DocumentType.AUDIO, b"fake-audio-bytes", transcription_provider=FakeTranscriber())
    assert result.text == "this is the transcript"


def test_unsupported_type_raises():
    from memory_platform.core.exceptions import UnsupportedDocumentTypeError
    with pytest.raises((UnsupportedDocumentTypeError, ValueError)):
        extractors.extract("not-a-real-type", b"data")
