"""Real text extraction per document type. PDF/DOCX/PPTX/XLSX use real
libraries (pypdf/python-docx/python-pptx/openpyxl); TEXT/MARKDOWN/CSV/
JSON/HTML are decoded directly. IMAGE/AUDIO/VIDEO are OCR-ready /
transcript-ready — real OCR and ASR engines are out of scope for this
build (no redistributable OCR/ASR model ships in this sandbox), so those
three types go through a documented `TranscriptionProvider` seam that
raises a clear `DocumentProcessingError` by default rather than silently
faking a transcript. Swapping in a real OCR/ASR provider means
implementing that one small interface — no changes to the pipeline.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from typing import Protocol

from memory_platform.core.exceptions import DocumentProcessingError, UnsupportedDocumentTypeError
from memory_platform.domain.enums import DocumentType

_OCR_ASR_TYPES = {DocumentType.IMAGE, DocumentType.AUDIO, DocumentType.VIDEO}


@dataclass
class ExtractionResult:
    text: str
    page_count: int | None = None
    extra_metadata: dict | None = None


class TranscriptionProvider(Protocol):
    """The seam a real OCR engine (image -> text) or ASR engine
    (audio/video -> transcript) plugs into. Not implemented here by
    design — see module docstring."""

    def transcribe(self, raw_bytes: bytes, *, document_type: DocumentType) -> str: ...


class NotImplementedTranscriptionProvider:
    def transcribe(self, raw_bytes: bytes, *, document_type: DocumentType) -> str:
        raise DocumentProcessingError(
            f"No TranscriptionProvider configured — {document_type.value} ingestion requires a real OCR/ASR "
            f"engine to be registered via DocumentProcessingService(transcription_provider=...). This build "
            f"intentionally does not fake transcription."
        )


def _strip_html(raw: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract(
    document_type: DocumentType | str, raw_bytes: bytes, *, filename: str | None = None, transcription_provider: TranscriptionProvider | None = None,
) -> ExtractionResult:
    dtype = DocumentType(document_type) if isinstance(document_type, str) else document_type

    if dtype == DocumentType.PDF:
        return _extract_pdf(raw_bytes)
    if dtype == DocumentType.DOCX:
        return _extract_docx(raw_bytes)
    if dtype == DocumentType.PPTX:
        return _extract_pptx(raw_bytes)
    if dtype == DocumentType.XLSX:
        return _extract_xlsx(raw_bytes)
    if dtype == DocumentType.CSV:
        return _extract_csv(raw_bytes)
    if dtype == DocumentType.JSON:
        return ExtractionResult(text=json.dumps(json.loads(raw_bytes.decode("utf-8")), indent=2))
    if dtype == DocumentType.HTML or dtype == DocumentType.WEBPAGE:
        return ExtractionResult(text=_strip_html(raw_bytes.decode("utf-8", errors="replace")))
    if dtype in (DocumentType.MARKDOWN, DocumentType.TEXT):
        return ExtractionResult(text=raw_bytes.decode("utf-8", errors="replace"))
    if dtype in _OCR_ASR_TYPES:
        provider = transcription_provider or NotImplementedTranscriptionProvider()
        return ExtractionResult(text=provider.transcribe(raw_bytes, document_type=dtype))
    raise UnsupportedDocumentTypeError(f"No extractor registered for document type '{dtype.value}'")


def _extract_pdf(raw_bytes: bytes) -> ExtractionResult:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return ExtractionResult(text="\n\n".join(pages), page_count=len(pages))
    except Exception as exc:  # noqa: BLE001
        raise DocumentProcessingError(f"PDF extraction failed: {exc}") from exc


def _extract_docx(raw_bytes: bytes) -> ExtractionResult:
    from docx import Document

    try:
        doc = Document(io.BytesIO(raw_bytes))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return ExtractionResult(text="\n".join(parts))
    except Exception as exc:  # noqa: BLE001
        raise DocumentProcessingError(f"DOCX extraction failed: {exc}") from exc


def _extract_pptx(raw_bytes: bytes) -> ExtractionResult:
    from pptx import Presentation

    try:
        prs = Presentation(io.BytesIO(raw_bytes))
        parts = []
        slide_count = 0
        for i, slide in enumerate(prs.slides):
            slide_count = i + 1
            slide_text = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = "".join(run.text for run in para.runs)
                        if text.strip():
                            slide_text.append(text)
            if slide_text:
                parts.append(f"[Slide {i + 1}] " + " ".join(slide_text))
        return ExtractionResult(text="\n".join(parts), page_count=slide_count)
    except Exception as exc:  # noqa: BLE001
        raise DocumentProcessingError(f"PPTX extraction failed: {exc}") from exc


def _extract_xlsx(raw_bytes: bytes) -> ExtractionResult:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(raw_bytes), data_only=True)
        parts = []
        for sheet in wb.worksheets:
            parts.append(f"[Sheet: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    parts.append(" | ".join(cells))
        return ExtractionResult(text="\n".join(parts), extra_metadata={"sheet_count": len(wb.worksheets)})
    except Exception as exc:  # noqa: BLE001
        raise DocumentProcessingError(f"XLSX extraction failed: {exc}") from exc


def _extract_csv(raw_bytes: bytes) -> ExtractionResult:
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = [" | ".join(row) for row in reader]
        return ExtractionResult(text="\n".join(rows), extra_metadata={"row_count": len(rows)})
    except Exception as exc:  # noqa: BLE001
        raise DocumentProcessingError(f"CSV extraction failed: {exc}") from exc
