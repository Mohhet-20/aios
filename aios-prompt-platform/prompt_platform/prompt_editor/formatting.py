"""Deterministic prompt formatting — trims trailing whitespace, collapses
excess blank lines, normalizes line endings. Intentionally conservative:
it never touches content inside `{{variable}}` placeholders or reorders
text, so formatting a template can't silently change its meaning."""
from __future__ import annotations

import re

_TRAILING_WS_RE = re.compile(r"[ \t]+(?=\n|$)")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def format_template(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _TRAILING_WS_RE.sub("", normalized)
    normalized = _EXCESS_BLANK_LINES_RE.sub("\n\n", normalized)
    return normalized.strip("\n")
