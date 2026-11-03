"""DocumentReaderHandler: genuinely parses what this reference build can
parse without a heavy binary-format dependency (plain text and CSV, via
Python's own `csv` module) — and is explicit, not silent, about what it
can't: PDF/Word/Excel/OCR need a real parsing library (pypdf/python-docx/
openpyxl/pytesseract) this platform doesn't bundle. Calling this
connector for those formats raises a clear `ToolExecutionError` naming
the missing capability, the same disclosure precedent the Memory
Platform's document-intelligence pipeline set for OCR/ASR: no plausible-
looking fake output for a format the reference build can't actually
read."""
from __future__ import annotations

import csv
import io
from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler

_UNSUPPORTED_FORMATS = {
    "pdf": "PDF parsing requires a library such as pypdf, not bundled in this reference build",
    "docx": "Word document parsing requires a library such as python-docx, not bundled in this reference build",
    "xlsx": "Excel parsing requires a library such as openpyxl, not bundled in this reference build",
    "image": "OCR requires a library such as pytesseract plus the tesseract binary, not bundled in this reference build",
}


class DocumentReaderHandler(ConnectorHandler):
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        doc_format = (ctx.input_data.get("format") or ctx.config.get("format", "text")).lower()
        content = ctx.input_data.get("content")
        if content is None:
            raise ToolExecutionError("document_reader tool call requires 'content'")

        if doc_format in _UNSUPPORTED_FORMATS:
            raise ToolExecutionError(_UNSUPPORTED_FORMATS[doc_format])

        if doc_format == "csv":
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            return {"rows": rows, "row_count": len(rows), "columns": reader.fieldnames or []}

        if doc_format == "text":
            return {"text": content, "length": len(content)}

        raise ToolExecutionError(f"unsupported document format: '{doc_format}'")
