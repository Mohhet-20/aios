"""MediaProcessingHandler: image/audio/video processing needs real
libraries (Pillow/ffmpeg/whisper, ...) this reference build doesn't
bundle. Rather than fabricate plausible-looking output, this handler
always raises a clear, honest error naming what's missing — the same
disclosure precedent `document_reader.py` follows for PDF/Word/Excel/OCR.
A production deployment implements this connector for real by swapping
this one file; the tool/version schema and execution engine don't
change."""
from __future__ import annotations

from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class MediaProcessingHandler(ConnectorHandler):
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        media_type = ctx.input_data.get("media_type") or ctx.config.get("media_type", "unknown")
        raise ToolExecutionError(
            f"media processing for '{media_type}' requires a real media library (e.g. Pillow, ffmpeg, "
            "whisper) not bundled in this reference build — implement this connector for your deployment "
            "by registering a real handler under connector_key='media_processing'"
        )
