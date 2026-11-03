"""Response filtering: redacts caller-supplied banned patterns
(regexes) from AI-generated output before it reaches the end user —
the last line of defense after prompt-level guardrails, catching
things that slipped through into the model's own response (e.g. a
model echoing back a secret it was shown, or producing content that
matches an organization's banned-terms list)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FilterResult:
    filtered_text: str
    redaction_count: int


def filter_response(text: str, banned_patterns: list[str], *, placeholder: str = "[FILTERED]") -> FilterResult:
    filtered = text
    count = 0
    for pattern in banned_patterns:
        filtered, n = re.subn(pattern, placeholder, filtered, flags=re.IGNORECASE)
        count += n
    return FilterResult(filtered_text=filtered, redaction_count=count)
