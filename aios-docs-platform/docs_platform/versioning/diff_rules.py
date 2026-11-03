"""Pure text-diff computation — no DB/service imports. A thin wrapper
over `difflib.unified_diff` so `DocVersionService.diff` stays
testable and swappable without touching the standard library import
in more than one place."""
from __future__ import annotations

import difflib


def compute_diff(old_text: str, new_text: str, *, from_label: str = "old", to_label: str = "new") -> list[str]:
    return list(
        difflib.unified_diff(
            old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
            fromfile=from_label, tofile=to_label, lineterm="",
        )
    )
